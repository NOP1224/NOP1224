#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


REPOS = [
    {
        "name": "Unaligned RGB-T Tracking",
        "full": "NOP1224/Unaligned_RGBT_Tracking",
        "role": "Lead / Maintainer",
    },
    {
        "name": "OpenPAR",
        "full": "Event-AHU/OpenPAR",
        "role": "Contributor",
    },
]

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "NOP1224")

AUTHOR_REGEX = os.getenv(
    "AUTHOR_REGEX",
    r"NOP1224|Jiandong Jin|Jin Jiandong|jinjiandong|jiandong",
)

AUTHOR_RE = re.compile(AUTHOR_REGEX, re.IGNORECASE)

RECENT_DAYS = int(os.getenv("RECENT_DAYS", "90"))

START = "<!-- PROJECT-STATS:START -->"
END = "<!-- PROJECT-STATS:END -->"


def run(cmd, cwd=None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result.stdout.strip()


def pct(a, b):
    if b == 0:
        return 0.0
    return 100.0 * a / b


def match_author(name, email):
    identity = f"{name} <{email}>"
    return bool(AUTHOR_RE.search(identity))


def clone_repo(repo_full, dst):
    url = f"https://github.com/{repo_full}.git"
    run([
        "git",
        "clone",
        "--quiet",
        "--single-branch",
        "--no-tags",
        url,
        str(dst),
    ])


def count_commits(repo_dir, since=None):
    args = ["git", "log", "--format=%H%x00%an%x00%ae"]

    if since is not None:
        args.append(f"--since={since}")

    out = run(args, cwd=repo_dir)

    if not out:
        return 0, 0

    total = 0
    mine = 0

    for line in out.splitlines():
        parts = line.split("\x00")
        if len(parts) != 3:
            continue

        _, name, email = parts
        total += 1

        if match_author(name, email):
            mine += 1

    return mine, total


def count_line_changes(repo_dir):
    out = run(
        [
            "git",
            "log",
            "--numstat",
            "--format=__AUTHOR__%an <%ae>",
        ],
        cwd=repo_dir,
    )

    total_change = 0
    my_change = 0
    current_is_mine = False

    for line in out.splitlines():
        if line.startswith("__AUTHOR__"):
            identity = line.replace("__AUTHOR__", "")
            current_is_mine = bool(AUTHOR_RE.search(identity))
            continue

        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        add, delete = parts[0], parts[1]

        # Binary files are shown as "-"
        if not add.isdigit() or not delete.isdigit():
            continue

        delta = int(add) + int(delete)
        total_change += delta

        if current_is_mine:
            my_change += delta

    return my_change, total_change


def latest_commit_time(repo_dir):
    try:
        return run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=repo_dir,
        )
    except Exception:
        return "N/A"


def github_json(api_path):
    token = os.getenv("GITHUB_TOKEN", "")
    url = f"https://api.github.com{api_path}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def github_search_count(query):
    encoded = urllib.parse.urlencode({"q": query, "per_page": 1})
    data = github_json(f"/search/issues?{encoded}")
    return int(data.get("total_count", 0) or 0)


def get_repo_meta(repo_full):
    data = github_json(f"/repos/{repo_full}")

    return {
        "stars": int(data.get("stargazers_count", 0) or 0),
        "forks": int(data.get("forks_count", 0) or 0),
        "open_issues": int(data.get("open_issues_count", 0) or 0),
    }


def get_github_activity(repo_full):
    my_prs = github_search_count(
        f"repo:{repo_full} type:pr author:{GITHUB_USERNAME}"
    )
    my_issues = github_search_count(
        f"repo:{repo_full} type:issue author:{GITHUB_USERNAME}"
    )

    return {
        "my_prs": my_prs,
        "my_issues": my_issues,
    }


def contribution_level(commit_rate, change_rate, recent_rate):
    score = 0.50 * commit_rate + 0.30 * change_rate + 0.20 * recent_rate

    if score >= 70:
        return "Primary"
    if score >= 40:
        return "Major"
    if score >= 15:
        return "Active"
    if score > 0:
        return "Occasional"
    return "Unclear"


def collect_repo_stats(repo):
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / repo["full"].replace("/", "__")
        clone_repo(repo["full"], repo_dir)

        my_commits, total_commits = count_commits(repo_dir)
        my_recent, total_recent = count_commits(
            repo_dir,
            since=f"{RECENT_DAYS}.days",
        )

        my_change, total_change = count_line_changes(repo_dir)

        latest_time = latest_commit_time(repo_dir)
        meta = get_repo_meta(repo["full"])
        activity = get_github_activity(repo["full"])

        commit_rate = pct(my_commits, total_commits)
        change_rate = pct(my_change, total_change)
        recent_rate = pct(my_recent, total_recent)

        level = contribution_level(
            commit_rate=commit_rate,
            change_rate=change_rate,
            recent_rate=recent_rate,
        )

        return {
            "project": repo["name"],
            "repo": repo["full"],
            "role": repo["role"],
            "my_commits": my_commits,
            "total_commits": total_commits,
            "commit_rate": commit_rate,
            "my_change": my_change,
            "total_change": total_change,
            "change_rate": change_rate,
            "my_recent": my_recent,
            "total_recent": total_recent,
            "recent_rate": recent_rate,
            "stars": meta["stars"],
            "forks": meta["forks"],
            "open_issues": meta["open_issues"],
            "my_prs": activity["my_prs"],
            "my_issues": activity["my_issues"],
            "latest_time": latest_time,
            "level": level,
        }


def build_stats():
    rows = []

    for repo in REPOS:
        try:
            rows.append(collect_repo_stats(repo))
        except Exception as e:
            rows.append({
                "project": repo["name"],
                "repo": repo["full"],
                "role": repo["role"],
                "error": str(e),
            })

    return rows


def fmt_num(x):
    return f"{x:,}"


def render_markdown(rows):
    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")

    lines = []
    lines.append(f"_Last updated: {updated_at}_")
    lines.append("")
    lines.append("| Project | Role | Contribution Level | Commit Share | Code Change Share | Recent 90-Day Commits | PRs / Issues | Stars / Forks | Last Commit |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")

    for r in rows:
        project_link = f"[{r['project']}](https://github.com/{r['repo']})"

        if "error" in r:
            lines.append(
                f"| {project_link} | {r['role']} | Error | - | - | - | - | - | Failed to update |"
            )
            continue

        commit_cell = (
            f"{r['my_commits']} / {r['total_commits']} "
            f"({r['commit_rate']:.1f}%)"
        )

        change_cell = (
            f"{fmt_num(r['my_change'])} / {fmt_num(r['total_change'])} "
            f"({r['change_rate']:.1f}%)"
        )

        recent_cell = (
            f"{r['my_recent']} / {r['total_recent']} "
            f"({r['recent_rate']:.1f}%)"
        )

        pr_issue_cell = f"{r['my_prs']} / {r['my_issues']}"
        stars_cell = f"{r['stars']} / {r['forks']}"

        lines.append(
            f"| {project_link} | {r['role']} | {r['level']} | "
            f"{commit_cell} | {change_cell} | {recent_cell} | "
            f"{pr_issue_cell} | {stars_cell} | {r['latest_time']} |"
        )

    lines.append("")
    lines.append("**Metric definition:**")
    lines.append("")
    lines.append("- **Commit Share** = matched author commits / total commits on the default branch.")
    lines.append("- **Code Change Share** = matched author additions and deletions / total additions and deletions on the default branch.")
    lines.append("- **Recent 90-Day Commits** = matched author commits / total commits in the latest 90 days.")
    lines.append("- **PRs / Issues** = pull requests and issues authored by `NOP1224` in the repository.")
    lines.append("- Binary files are ignored in line-change statistics.")

    return "\n".join(lines)


def update_readme(block):
    readme = Path("README.md")

    if not readme.exists():
        raise FileNotFoundError("README.md not found in repository root.")

    text = readme.read_text(encoding="utf-8")

    if START not in text or END not in text:
        text += f"\n\n## Project Contribution & Activity\n\n{START}\n{END}\n"

    before = text.split(START)[0]
    after = text.split(END)[1]

    new_text = f"{before}{START}\n{block}\n{END}{after}"
    readme.write_text(new_text, encoding="utf-8")


def main():
    if shutil.which("git") is None:
        raise RuntimeError("git is not available in the current environment.")

    rows = build_stats()
    block = render_markdown(rows)
    update_readme(block)


if __name__ == "__main__":
    main()