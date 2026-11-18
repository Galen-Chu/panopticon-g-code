"""
Outer Axis — G-Code Ecosystem Health Monitor · 生態系統健康監控

Monitors the health of the ecosystem repositories via the GitHub API:
repository metadata plus CI/CD (workflow run) health.
Part of the Panopticon G-Code dual-axis awareness system.
"""
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# Ecosystem repositories: G-Code family + actively automated projects.
# Override with a comma-separated PANOPTICON_REPOS environment variable.
G_CODE_REPOS = [
    "spiritual-g-code",
    "sync-g-code",
    "psychological-g-code",
    "physiological-g-code",
    "program-g-code",
    "skill-g-code",
    "spec-g-code",
    "panopticon-g-code",
    "pms-test-automation-script",
    "TEXT-Message",
]

GITHUB_USER = "Galen-Chu"
MONITOR_DIR = Path(__file__).parent.parent.parent / "data" / "monitor"

# CI health: how many recent completed runs to inspect, and the failure
# count that counts as "unhealthy pipeline"
CI_WINDOW_RUNS = 15
CI_FAILURE_THRESHOLD = 2

# Rate limits / server errors worth retrying. GitHub's secondary rate
# limit answers 403 with a Retry-After header, which we honor.
RETRYABLE_CODES = {403, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 5

# Repos are checked in parallel; 5 workers × 2 calls keeps us far below
# rate limits while turning 20 sequential calls into ~4 rounds.
MAX_PARALLEL_CHECKS = 5


def _api_headers() -> dict:
    """Auth headers when GITHUB_TOKEN is present (raises rate limit 60/h → 1000/h)."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"}
    return {"Accept": "application/vnd.github+json"}


def _retry_delay(response, attempt: int) -> float:
    """Seconds to wait before the next attempt: Retry-After if GitHub sent
    one, otherwise linear backoff."""
    value = response.headers.get("Retry-After", "")
    try:
        return max(float(value), 1.0)
    except (TypeError, ValueError):
        return BASE_BACKOFF_SECONDS * attempt


def _api_get(url: str, params: dict = None):
    """GET a GitHub API URL with retry/backoff on rate limits and 5xx.

    Returns the last response even if it is still failing, so callers can
    degrade through their normal error handling instead of crashing the run.
    """
    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.get(url, timeout=10, headers=_api_headers(), params=params)
        if response.status_code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS:
            return response
        delay = _retry_delay(response, attempt)
        print(f"  ⚠ HTTP {response.status_code} — retry {attempt}/{MAX_ATTEMPTS - 1} "
              f"in {delay:.0f}s")
        time.sleep(delay)
    return response


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def check_repo_health(repo_name: str) -> dict:
    """Check a single repository's health via the GitHub API."""
    if requests is None:
        return {"repo": repo_name, "status": "error", "message": "requests not installed"}

    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}"
    try:
        response = _api_get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "repo": repo_name,
                "status": "healthy",
                "stars": data.get("stargazers_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "last_push": data.get("pushed_at", ""),
                "default_branch": data.get("default_branch", "main"),
                "size_kb": data.get("size", 0),
            }
        elif response.status_code == 404:
            return {"repo": repo_name, "status": "not_found"}
        else:
            return {"repo": repo_name, "status": "error", "code": response.status_code}
    except requests.RequestException as e:
        return {"repo": repo_name, "status": "error", "message": str(e)}


def check_workflow_health(repo_name: str) -> dict:
    """Check a repository's CI/CD health: failures among recent completed runs."""
    if requests is None:
        return {"repo": repo_name, "status": "unavailable", "message": "requests not installed"}

    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/actions/runs"
    try:
        response = _api_get(
            url, params={"per_page": CI_WINDOW_RUNS, "status": "completed"})
        if response.status_code != 200:
            return {"repo": repo_name, "status": "unavailable",
                    "code": response.status_code}
        runs = response.json().get("workflow_runs", [])
        completed = [r for r in runs if r.get("status") == "completed"]
        failures = [r for r in completed if r.get("conclusion") == "failure"]
        last_failure = next(
            ({"workflow": r.get("name", ""), "created_at": r.get("created_at", "")}
             for r in failures), None)
        return {
            "repo": repo_name,
            "status": "failing" if len(failures) >= CI_FAILURE_THRESHOLD else "ok",
            "checked_runs": len(completed),
            "failed_runs": len(failures),
            "threshold": CI_FAILURE_THRESHOLD,
            "last_failure": last_failure,
        }
    except requests.RequestException as e:
        return {"repo": repo_name, "status": "unavailable", "message": str(e)}


def get_repo_list() -> list:
    """Repository list, overridable via PANOPTICON_REPOS (comma-separated)."""
    override = os.environ.get("PANOPTICON_REPOS", "").strip()
    if override:
        return [r.strip() for r in override.split(",") if r.strip()]
    return list(G_CODE_REPOS)


def _check_repo_full(repo_name: str) -> dict:
    """Metadata + CI health for one repo (the unit of parallel work)."""
    result = check_repo_health(repo_name)
    if result["status"] == "healthy":
        result["ci"] = check_workflow_health(repo_name)
    return result


def check_all_repos() -> list:
    """Check all ecosystem repositories (metadata + CI/CD health).

    Repos run through a small thread pool — 20 sequential API calls used
    to dominate the runtime. Output order still follows the repo list.
    """
    repos = get_repo_list()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CHECKS) as pool:
        results = list(pool.map(_check_repo_full, repos))

    for result in results:
        status_icon = {"healthy": "✓", "not_found": "?", "error": "✗"}.get(result["status"], " ")
        ci = result.get("ci", {})
        ci_icon = {"failing": "⚡", "ok": "·"}.get(ci.get("status", ""), " ")
        print(f"  [{status_icon}{ci_icon}] {result['repo']}: {result['status']}"
              + (f" (CI: {ci.get('failed_runs', '?')}/{ci.get('checked_runs', '?')} failed)"
                 if ci else ""))
    return results


def save_report(results: list) -> Path:
    """Save the health report to the data directory."""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    now = _utcnow()
    filepath = MONITOR_DIR / f"health_{now.strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "timestamp": now.isoformat(),
        "total_repos": len(results),
        "healthy": sum(1 for r in results if r["status"] == "healthy"),
        "issues": sum(1 for r in results if r["status"] != "healthy"),
        "ci_failing": sum(1 for r in results
                          if r.get("ci", {}).get("status") == "failing"),
        "repos": results,
    }

    filepath.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return filepath


def main():
    """CLI entry point."""
    import argparse
    import sys

    # Windows consoles often default to a legacy codepage (e.g. cp950) that
    # can't encode the status icons — degrade to '?' instead of crashing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Panopticon Outer Axis — Ecosystem Monitor")
    parser.add_argument("--all", action="store_true", help="Check all ecosystem repos")
    parser.add_argument("--repo", type=str, help="Check a specific repo")
    parser.add_argument("--save", action="store_true", help="Save report to data directory")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Panopticon Ecosystem Monitor")
    print(f"  {_utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    if args.repo:
        result = check_repo_health(args.repo)
        result["ci"] = check_workflow_health(args.repo)
        results = [result]
        print(f"  {result}")
    else:
        results = check_all_repos()

    healthy = sum(1 for r in results if r["status"] == "healthy")
    ci_failing = sum(1 for r in results if r.get("ci", {}).get("status") == "failing")
    print(f"\n  Ecosystem health: {healthy}/{len(results)} repos healthy"
          + (f", {ci_failing} with failing CI" if ci_failing else ""))

    if args.save:
        filepath = save_report(results)
        print(f"  Report saved: {filepath}")

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    main()
