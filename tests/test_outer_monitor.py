"""Tests for the Outer Axis ecosystem monitor."""
from unittest.mock import patch, MagicMock

from outer.monitor.checker import check_repo_health, G_CODE_REPOS


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
