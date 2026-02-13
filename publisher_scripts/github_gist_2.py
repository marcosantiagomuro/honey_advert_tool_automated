# post to github gists using API token

import json
import requests
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_seeded_demo_script

TOKEN = need("GITHUB_API_GIST_TOKEN_4")


API = "https://api.github.com/gists"

post = make_seeded_demo_script()


payload = {
    "description": "ssh execution script",
    "public": True,
    "files": {
        post["filename"]: {"content": post["content"]},
        "ssh server payload.md.md": {
            "content": "commit where to save script for ssh payoload execution"
        },
    },
}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "python-gist-script"
}

r = requests.post(API, headers=headers, json=payload, timeout=30)
print("status:", r.status_code)
print("response:", r.text)
r.raise_for_status()
data = r.json()

print(f"""
====================================================
GitHub Gist created successfully.
RESULT_URL: {data.get("html_url")}
====================================================
""")
