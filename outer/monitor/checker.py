"""
Outer Axis — G-Code Ecosystem Health Monitor · 生態系統健康監控

Monitors the health of all G-Code repositories via the GitHub API.
Part of the Panopticon G-Code dual-axis awareness system.
"""
import os
import json
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# All G-Code family repositories
G_CODE_REPOS = [
    "spiritual-g-code",
    "sync-g-code",
    "psychological-g-code",
    "physiological-g-code",
    "program-g-code",
    "skill-g-code",
    "spec-g-code",
    "panopticon-g-code",
]

GITHUB_USER = "Galen-Chu"
MONITOR_DIR = Path(__file__).parent.parent.parent / "data" / "monitor"


def check_repo_health(repo_name: str) -> dict:
    """Check a single repository's health via the GitHub API."""
    if requests is None:
        return {"repo": repo_name, "status": "error", "message": "requests not installed"}

    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}"
    try:
        response = requests.get(url, timeout=10)
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


def check_all_repos() -> list:
    """Check all G-Code repositories."""
    results = []
    for repo in G_CODE_REPOS:
        result = check_repo_health(repo)
        results.append(result)
        status_icon = {"healthy": "✓", "not_found": "?", "error": "✗"}.get(result["status"], " ")
        print(f"  [{status_icon}] {repo}: {result['status']}")
    return results


def save_report(results: list) -> Path:
    """Save the health report to the data directory."""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow()
    filepath = MONITOR_DIR / f"health_{now.strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "timestamp": now.isoformat(),
        "total_repos": len(results),
        "healthy": sum(1 for r in results if r["status"] == "healthy"),
        "issues": sum(1 for r in results if r["status"] != "healthy"),
        "repos": results,
    }

    filepath.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return filepath


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Panopticon Outer Axis — Ecosystem Monitor")
    parser.add_argument("--all", action="store_true", help="Check all G-Code repos")
    parser.add_argument("--repo", type=str, help="Check a specific repo")
    parser.add_argument("--save", action="store_true", help="Save report to data directory")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Panopticon Ecosystem Monitor")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    if args.repo:
        result = check_repo_health(args.repo)
        results = [result]
        print(f"  {result}")
    else:
        results = check_all_repos()

    healthy = sum(1 for r in results if r["status"] == "healthy")
    print(f"\n  Ecosystem health: {healthy}/{len(results)} repos healthy")

    if args.save:
        filepath = save_report(results)
        print(f"  Report saved: {filepath}")

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    main()
