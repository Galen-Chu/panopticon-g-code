"""Tests for the Outer Axis ecosystem monitor."""
from unittest.mock import patch, MagicMock

from outer.monitor.checker import (
    check_all_repos, check_repo_health, G_CODE_REPOS, MAX_ATTEMPTS,
)


class TestGCodeRepos:
    def test_all_repos_listed(self):
        assert len(G_CODE_REPOS) >= 8
        assert "panopticon-g-code" in G_CODE_REPOS
        assert "spiritual-g-code" in G_CODE_REPOS


class TestCheckRepoHealth:
    @patch("outer.monitor.checker.requests")
    def test_healthy_repo(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 1,
            "open_issues_count": 0,
            "pushed_at": "2026-08-17T00:00:00Z",
            "default_branch": "main",
            "size": 100,
        }
        mock_requests.get.return_value = mock_response

        result = check_repo_health("test-repo")
        assert result["status"] == "healthy"
        assert result["stars"] == 1

    @patch("outer.monitor.checker.requests")
    def test_not_found_repo(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        result = check_repo_health("nonexistent-repo")
        assert result["status"] == "not_found"


class TestRateLimitRetry:
    @patch("outer.monitor.checker.time")
    @patch("outer.monitor.checker.requests")
    def test_retries_on_429_then_succeeds(self, mock_requests, mock_time):
        limited = MagicMock()
        limited.status_code = 429
        limited.headers = {"Retry-After": "7"}
        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {
            "stargazers_count": 1,
            "open_issues_count": 0,
            "pushed_at": "2026-11-01T00:00:00Z",
            "default_branch": "main",
            "size": 100,
        }
        mock_requests.get.side_effect = [limited, ok]

        result = check_repo_health("test-repo")

        assert result["status"] == "healthy"
        assert mock_requests.get.call_count == 2
        mock_time.sleep.assert_called_once_with(7.0)  # honors Retry-After

    @patch("outer.monitor.checker.time")
    @patch("outer.monitor.checker.requests")
    def test_gives_up_after_max_attempts(self, mock_requests, mock_time):
        limited = MagicMock()
        limited.status_code = 429
        limited.headers = {}  # no Retry-After → linear backoff
        mock_requests.get.return_value = limited

        result = check_repo_health("test-repo")

        assert result["status"] == "error"
        assert result["code"] == 429
        assert mock_requests.get.call_count == MAX_ATTEMPTS

    @patch("outer.monitor.checker.requests")
    def test_404_is_not_retried(self, mock_requests):
        not_found = MagicMock()
        not_found.status_code = 404
        mock_requests.get.return_value = not_found

        result = check_repo_health("gone-repo")

        assert result["status"] == "not_found"
        assert mock_requests.get.call_count == 1


class TestParallelChecks:
    @patch("outer.monitor.checker.check_workflow_health")
    @patch("outer.monitor.checker.check_repo_health")
    def test_all_repos_checked_in_list_order(self, mock_repo, mock_ci, monkeypatch):
        monkeypatch.setenv("PANOPTICON_REPOS", "repo-a,repo-b,repo-c")
        mock_repo.side_effect = lambda name: {
            "repo": name, "status": "healthy", "open_issues": 0, "last_push": ""}
        mock_ci.return_value = {"repo": "?", "status": "ok",
                                "checked_runs": 3, "failed_runs": 0}

        results = check_all_repos()

        assert [r["repo"] for r in results] == ["repo-a", "repo-b", "repo-c"]
        assert mock_repo.call_count == 3
        assert mock_ci.call_count == 3
        assert all(r["ci"]["status"] == "ok" for r in results)
