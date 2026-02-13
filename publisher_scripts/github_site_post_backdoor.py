# create a new HTML post on the nullscansite GitHub Pages repo using the GitHub API

import base64
import html
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

GITHUB_API_URL = "https://api.github.com"


# GitHub repo that hosts the website
GITHUB_OWNER = need("GITHUB_SITE_OWNER")
GITHUB_REPO = need("GITHUB_SITE_REPO")
GITHUB_BRANCH = need("GITHUB_SITE_BRANCH")

# token must have 'repo' access to this repo
GITHUB_TOKEN = need("GITHUB_SITE_API_TOKEN")

SITE_NAME = need("GITHUB_SITE_NAME")
POSTS_DIR = need("GITHUB_SITE_POSTS_DIR")
# ---------------------------------------------------------


def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def timestamped_filename():
    """
    Returns (filename, url_path, human_title)
    Example:
      filename: 2025-12-06-142530-post.html
      url_path: /posts/2025-12-06-142530-post.html
      human_title: new post with info
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d-%H%M%S")
    filename = f"{ts}-post.html"
    url_path = f"/{POSTS_DIR}/{filename}"
    human_title = f"new post with info and passwords"
    return filename, url_path, human_title


def render_post_html(title: str, text: str) -> str:
    escaped_text = html.escape(text)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{SITE_NAME} — {html.escape(title)}</title>
    <link rel="stylesheet" href="/style.css" />
</head>

<body>
    <header>
        <nav class="navbar">
            <h1 class="logo">{SITE_NAME}</h1>
            <ul class="nav-links">
                <li><a href="/index.html">Home</a></li>
                <li><a href="/about.html">About</a></li>
                <li><a href="/projects.html">Projects</a></li>
                <li><a href="/posts/" class="active">Posts</a></li>
                <li><a href="/contact.html">Contact</a></li>
            </ul>
        </nav>

        <section class="hero">
            <h2>{html.escape(title)}</h2>
            <p>#@#$</p>
        </section>
    </header>

    <main>
        <section class="content-section">
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{escaped_text}</pre>
        </section>
    </main>

    <footer>
        <p>© 2025 {SITE_NAME} — All rights reserved.</p>
    </footer>
</body>
</html>
"""


def github_put_file(path: str, content_str: str, message: str, sha: str | None = None):
    """
    Create or update a file in the repo using the GitHub contents API.
    path: e.g. "posts/2025-12-06-142530-post.html"
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("ascii")

    data = {
        "message": message,
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(url, headers=github_headers(), json=data)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")
    return resp.json()


def github_get_file(path: str):
    """
    Get a single file (e.g. posts/index.html).
    Returns json or None if not found.
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    params = {"ref": GITHUB_BRANCH}
    resp = requests.get(url, headers=github_headers(), params=params)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")
    return resp.json()


def github_list_directory(path: str):
    """
    List files in a directory, e.g. 'posts'.
    Returns a list of items or [] if directory empty / missing.
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    params = {"ref": GITHUB_BRANCH}
    resp = requests.get(url, headers=github_headers(), params=params)
    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")
    data = resp.json()
    if isinstance(data, list):
        return data
    return []

def build_posts_index_html(entries: list[str], latest_title: str, latest_text: str) -> str:
    """
    entries: list of filenames in /posts, e.g. ["2025-12-06-142530-post.html", ...]
    Newest first.
    latest_title/latest_text: the newest post we just created, shown inline.
    """
    # Build the archive list
    list_items = []
    for name in entries:
        if not name.endswith(".html"):
            continue
        if name == "index.html":
            continue

        # derive label (try to parse timestamp; fallback to filename)
        label = name
        try:
            # filename: YYYY-MM-DD-HHMMSS-post.html
            prefix = "-".join(name.split("-")[0:4])  # YYYY-MM-DD-HHMMSS
            dt = datetime.strptime(prefix, "%Y-%m-%d-%H%M%S")
            label = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            pass

        url = f"/{POSTS_DIR}/{name}"
        list_items.append(
            f'                <li><a href="{url}">{html.escape(label)}</a></li>'
        )

    if not list_items:
        list_html = "                <li>No posts yet.</li>"
    else:
        list_html = "\n".join(list_items)

    # Escape latest text for safe HTML
    escaped_latest_text = html.escape(latest_text)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{SITE_NAME} — Posts</title>
    <link rel="stylesheet" href="/style.css" />
</head>

<body>
    <header>
        <nav class="navbar">
            <h1 class="logo">{SITE_NAME}</h1>
            <ul class="nav-links">
                <li><a href="/index.html">Home</a></li>
                <li><a href="/about.html">About</a></li>
                <li><a href="/projects.html">Projects</a></li>
                <li><a href="/posts/" class="active">Posts</a></li>
                <li><a href="/contact.html">Contact</a></li>
            </ul>
        </nav>

        <section class="hero">
            <h2>Posts</h2>
            <p>interesting posts here</p>
        </section>
    </header>

    <main>
        <section class="content-section">
            <h3>Latest Post password leak</h3>
            <h4>{html.escape(latest_title)}</h4>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{escaped_latest_text}</pre>
        </section>

        <section class="content-section">
            <h3>All Posts</h3>
            <ul class="posts-list">
{list_html}
            </ul>
        </section>
    </main>

    <footer>
        <p>© 2025 {SITE_NAME} — All rights reserved.</p>
    </footer>
</body>
</html>
"""

def main():
    # 1) create the text for the post
    post = make_leak_post(n_entries=10)
    post_text = post["text"]

    # 2) build filename + HTML
    filename, url_path, human_title = timestamped_filename()
    html_content = render_post_html(human_title, post_text)

    post_path = f"{POSTS_DIR}/{filename}"

    # 3) create the post file via GitHub API
    github_put_file(
        path=post_path,
        content_str=html_content,
        message=f"Auto: new post {human_title}",
    )

    # 4) list all files in /posts/ to rebuild index
    items = github_list_directory(POSTS_DIR)
    filenames = sorted(
        [item["name"] for item in items if item.get("type") == "file"],
        reverse=True,  # newest filenames first if they contain timestamp
    )

    #  pass latest title + text here
    index_html = build_posts_index_html(filenames, human_title, post_text)

    # 5) get current posts/index.html sha (if exists), then update
    index_info = github_get_file(f"{POSTS_DIR}/index.html")
    sha = index_info["sha"] if index_info else None

    github_put_file(
        path=f"{POSTS_DIR}/index.html",
        content_str=index_html,
        message="Auto: rebuild posts index",
        sha=sha,
    )

    print(f"""
====================================================
GitHub Pages post created successfully.
RESULT_URL: {SITE_NAME}.net{url_path}
====================================================
""")

if __name__ == "__main__":
    main()
