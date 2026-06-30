#!/usr/bin/env python3
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


REPOS = [
    {
        "name": "Unaligned RGB-T Tracking",
        "full": "NOP1224/Unaligned_RGBT_Tracking",
        "role": "Lead / Maintainer",
        "color": "#0969DA",
        "accent": "#DDF4FF",
    },
    {
        "name": "OpenPAR",
        "full": "Event-AHU/OpenPAR",
        "role": "Contributor",
        "color": "#1A7F37",
        "accent": "#DAFBE1",
    },
]

AUTHOR_REGEX = os.getenv(
    "AUTHOR_REGEX",
    r"NOP1224|Jiandong Jin|Jin Jiandong|jinjiandong|jiandong",
)

AUTHOR_RE = re.compile(AUTHOR_REGEX, re.IGNORECASE)

OUT_DIR = Path("assets")
OUT_SVG = OUT_DIR / "project_contributions1.svg"


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


def count_commits(repo_dir):
    out = run(
        ["git", "log", "--format=%H%x00%an%x00%ae"],
        cwd=repo_dir,
    )

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


def get_repo_meta(repo_full):
    data = github_json(f"/repos/{repo_full}")

    return {
        "stars": int(data.get("stargazers_count", 0) or 0),
        "forks": int(data.get("forks_count", 0) or 0),
    }


def contribution_level(commit_rate, change_rate):
    score = 0.65 * commit_rate + 0.35 * change_rate

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
        my_change, total_change = count_line_changes(repo_dir)

        latest_time = latest_commit_time(repo_dir)
        meta = get_repo_meta(repo["full"])

        commit_rate = pct(my_commits, total_commits)
        change_rate = pct(my_change, total_change)

        return {
            "name": repo["name"],
            "full": repo["full"],
            "role": repo["role"],
            "color": repo["color"],
            "accent": repo["accent"],
            "my_commits": my_commits,
            "total_commits": total_commits,
            "commit_rate": commit_rate,
            "my_change": my_change,
            "total_change": total_change,
            "change_rate": change_rate,
            "level": contribution_level(commit_rate, change_rate),
            "stars": meta["stars"],
            "forks": meta["forks"],
            "latest_time": latest_time,
        }


def fmt_int(x):
    return f"{int(x):,}"


def progress_bar(x, y, width, height, rate, color, label, value):
    rate = max(0.0, min(100.0, rate))
    fill_w = width * rate / 100.0

    return f"""
    <text x="{x}" y="{y - 10}" class="label">{esc(label)}</text>
    <text x="{x + width}" y="{y - 10}" text-anchor="end" class="bar-value">{esc(value)}</text>

    <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#EAECEF"/>
    <rect x="{x}" y="{y}" width="{fill_w:.1f}" height="{height}" rx="8" fill="{color}"/>
    """


def metric_pill(x, y, w, label, value, color="#24292F", bg="#F6F8FA"):
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="42" rx="21" fill="{bg}" stroke="#D0D7DE"/>
    <text x="{x + 20}" y="{y + 26}" class="pill-label">{esc(label)}</text>
    <text x="{x + w - 18}" y="{y + 27}" text-anchor="end" class="pill-value" fill="{color}">{esc(value)}</text>
    """


def repo_card(repo, x, y, w, h):
    color = repo["color"]
    accent = repo["accent"]

    commit_value = (
        f"{repo['my_commits']}/{repo['total_commits']} "
        f"({repo['commit_rate']:.1f}%)"
    )

    change_value = (
        f"{fmt_int(repo['my_change'])}/{fmt_int(repo['total_change'])} "
        f"({repo['change_rate']:.1f}%)"
    )

    contribution_value = f"{repo['commit_rate']:.1f}%"

    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="#FFFFFF" stroke="#D0D7DE"/>

    <rect x="{x}" y="{y}" width="{w}" height="8" rx="4" fill="{color}"/>

    <text x="{x + 28}" y="{y + 48}" class="repo-title">{esc(repo['name'])}</text>
    <text x="{x + 28}" y="{y + 75}" class="repo-path">{esc(repo['full'])}</text>

    <rect x="{x + 28}" y="{y + 94}" width="126" height="30" rx="15" fill="{accent}" stroke="{color}" stroke-opacity="0.25"/>
    <text x="{x + 91}" y="{y + 115}" text-anchor="middle" class="level" fill="{color}">{esc(repo['level'])}</text>

    <text x="{x + 170}" y="{y + 115}" class="role">{esc(repo['role'])}</text>

    {progress_bar(
        x + 28,
        y + 168,
        w - 56,
        16,
        repo["commit_rate"],
        color,
        "Commit Share",
        commit_value,
    )}

    {progress_bar(
        x + 28,
        y + 238,
        w - 56,
        16,
        repo["change_rate"],
        color,
        "Code Change Share",
        change_value,
    )}

    {metric_pill(
        x + 28,
        y + 304,
        118,
        "★",
        str(repo["stars"]),
        "#BF8700",
        "#FFF8C5",
    )}

    {metric_pill(
        x + 158,
        y + 304,
        142,
        "Forks",
        str(repo["forks"]),
        "#57606A",
        "#F6F8FA",
    )}

    {metric_pill(
        x + 312,
        y + 304,
        w - 340,
        "Contribution",
        contribution_value,
        color,
        accent,
    )}

    <text x="{x + 28}" y="{y + 382}" class="last-commit">
      Last commit: {esc(repo['latest_time'])}
    </text>
    """


def render_svg(rows):
    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")

    width = 1120
    height = 530

    card_w = 530
    card_h = 410

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Project Contribution Dashboard">
  <style>
    .title {{
      font: 800 30px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}

    .subtitle {{
      font: 500 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}

    .repo-title {{
      font: 800 23px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}

    .repo-path {{
      font: 500 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}

    .level {{
      font: 800 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}

    .role {{
      font: 700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}

    .label {{
      font: 700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #24292F;
    }}

    .bar-value {{
      font: 600 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}

    .pill-label {{
      font: 800 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #57606A;
    }}

    .pill-value {{
      font: 800 16px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}

    .last-commit {{
      font: 500 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #6E7781;
    }}

    .note {{
      font: 500 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #6E7781;
    }}
  </style>

  <rect x="0" y="0" width="{width}" height="{height}" rx="28" fill="#F6F8FA"/>

  <text x="32" y="48" class="title">Research Project Contribution</text>
  <text x="32" y="76" class="subtitle">
    Auto-generated from default-branch Git history · Updated: {esc(updated_at)}
  </text>

  {repo_card(rows[0], 30, 96, card_w, card_h)}
  {repo_card(rows[1], 560, 96, card_w, card_h)}

  <text x="32" y="520" class="note">
    Contribution = matched author commits / total commits. Code change = additions + deletions. Binary files are ignored.
  </text>
</svg>
"""


def main():
    if shutil.which("git") is None:
        raise RuntimeError("git is not available.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = [collect_repo_stats(repo) for repo in REPOS]

    svg = render_svg(rows)
    OUT_SVG.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()