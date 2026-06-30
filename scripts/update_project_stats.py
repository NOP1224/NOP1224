#!/usr/bin/env python3
import html
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
        "color": "#2F80ED",
    },
    {
        "name": "OpenPAR",
        "full": "Event-AHU/OpenPAR",
        "role": "Contributor",
        "color": "#27AE60",
    },
]

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "NOP1224")
AUTHOR_REGEX = os.getenv(
    "AUTHOR_REGEX",
    r"NOP1224|Jiandong Jin|Jin Jiandong|jinjiandong|jiandong",
)
AUTHOR_RE = re.compile(AUTHOR_REGEX, re.IGNORECASE)
RECENT_DAYS = int(os.getenv("RECENT_DAYS", "90"))

OUT_DIR = Path("assets")
OUT_SVG = OUT_DIR / "project_contributions.svg"


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


def esc(s):
    return html.escape(str(s), quote=True)


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

        # Binary files appear as "-"
        if not add.isdigit() or not delete.isdigit():
            continue

        delta = int(add) + int(delete)
        total_change += delta

        if current_is_mine:
            my_change += delta

    return my_change, total_change


def latest_commit_time(repo_dir):
    try:
        return run(["git", "log", "-1", "--format=%ci"], cwd=repo_dir)
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
        my_recent, total_recent = count_commits(repo_dir, since=f"{RECENT_DAYS}.days")
        my_change, total_change = count_line_changes(repo_dir)

        latest_time = latest_commit_time(repo_dir)
        meta = get_repo_meta(repo["full"])
        activity = get_github_activity(repo["full"])

        commit_rate = pct(my_commits, total_commits)
        change_rate = pct(my_change, total_change)
        recent_rate = pct(my_recent, total_recent)

        return {
            "name": repo["name"],
            "full": repo["full"],
            "role": repo["role"],
            "color": repo["color"],
            "my_commits": my_commits,
            "total_commits": total_commits,
            "commit_rate": commit_rate,
            "my_change": my_change,
            "total_change": total_change,
            "change_rate": change_rate,
            "my_recent": my_recent,
            "total_recent": total_recent,
            "recent_rate": recent_rate,
            "level": contribution_level(commit_rate, change_rate, recent_rate),
            "stars": meta["stars"],
            "forks": meta["forks"],
            "open_issues": meta["open_issues"],
            "my_prs": activity["my_prs"],
            "my_issues": activity["my_issues"],
            "latest_time": latest_time,
        }


def fmt_int(x):
    return f"{int(x):,}"


def bar(x, y, width, height, rate, color, label, value):
    rate = max(0.0, min(100.0, rate))
    fill_w = width * rate / 100.0

    return f"""
    <text x="{x}" y="{y - 8}" class="label">{esc(label)}</text>
    <text x="{x + width}" y="{y - 8}" text-anchor="end" class="value">{esc(value)}</text>
    <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#EAECEF"/>
    <rect x="{x}" y="{y}" width="{fill_w:.1f}" height="{height}" rx="7" fill="{color}"/>
    """


def repo_card(repo, x, y, w, h):
    color = repo["color"]
    repo_url = f"https://github.com/{repo['full']}"

    commit_value = (
        f"{repo['my_commits']}/{repo['total_commits']} "
        f"({repo['commit_rate']:.1f}%)"
    )
    change_value = (
        f"{fmt_int(repo['my_change'])}/{fmt_int(repo['total_change'])} "
        f"({repo['change_rate']:.1f}%)"
    )
    recent_value = (
        f"{repo['my_recent']}/{repo['total_recent']} "
        f"({repo['recent_rate']:.1f}%)"
    )

    return f"""
    <a href="{esc(repo_url)}">
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#FFFFFF" stroke="#D0D7DE"/>
      <text x="{x + 28}" y="{y + 42}" class="repo-title">{esc(repo['name'])}</text>
      <text x="{x + 28}" y="{y + 70}" class="repo-sub">{esc(repo['full'])}</text>

      <rect x="{x + 28}" y="{y + 92}" width="128" height="28" rx="14" fill="{color}" opacity="0.12"/>
      <text x="{x + 92}" y="{y + 111}" text-anchor="middle" class="tag" fill="{color}">{esc(repo['level'])}</text>

      <text x="{x + 170}" y="{y + 111}" class="role">{esc(repo['role'])}</text>

      {bar(x + 28, y + 158, w - 56, 14, repo['commit_rate'], color, "Commit Share", commit_value)}
      {bar(x + 28, y + 218, w - 56, 14, repo['change_rate'], color, "Code Change Share", change_value)}
      {bar(x + 28, y + 278, w - 56, 14, repo['recent_rate'], color, f"Recent {RECENT_DAYS}-Day Commits", recent_value)}

      <text x="{x + 28}" y="{y + 342}" class="small">
        ★ {repo['stars']}   Forks {repo['forks']}   PRs {repo['my_prs']}   Issues {repo['my_issues']}
      </text>
      <text x="{x + 28}" y="{y + 368}" class="small-muted">
        Last commit: {esc(repo['latest_time'])}
      </text>
    </a>
    """


def render_svg(rows):
    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")

    width = 1100
    height = 520

    cards = []
    card_w = 520
    card_h = 400

    cards.append(repo_card(rows[0], 30, 92, card_w, card_h))
    cards.append(repo_card(rows[1], 550, 92, card_w, card_h))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Project Contribution Dashboard">
  <style>
    .title {{
      font: 700 28px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}
    .subtitle {{
      font: 400 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}
    .repo-title {{
      font: 700 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}
    .repo-sub {{
      font: 400 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}
    .tag {{
      font: 700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}
    .role {{
      font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}
    .label {{
      font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}
    .value {{
      font: 500 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}
    .small {{
      font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}
    .small-muted {{
      font: 400 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #6E7781;
    }}
  </style>

  <rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="#F6F8FA"/>

  <text x="30" y="44" class="title">Project Contribution Dashboard</text>
  <text x="30" y="70" class="subtitle">
    Auto-generated from default-branch Git history · Updated: {esc(updated_at)}
  </text>

  {''.join(cards)}

  <text x="30" y="507" class="small-muted">
    Commit Share = matched author commits / total commits · Code Change Share = additions + deletions · Binary files ignored.
  </text>
</svg>
"""


def main():
    if shutil.which("git") is None:
        raise RuntimeError("git is not available.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for repo in REPOS:
        rows.append(collect_repo_stats(repo))

    svg = render_svg(rows)
    OUT_SVG.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()