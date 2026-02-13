import requests
import json
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_seeded_demo_script


TOKEN = need("GITLAB_API_SNIPPET_TOKEN_5")

GITLAB_URL = "https://gitlab.com"

# API endpoint
url = f"{GITLAB_URL}/api/v4/snippets"

# Prepare data
post = make_seeded_demo_script()

payload = {
    "title": "commit with ssh payload execution",
    "visibility": "public",
    "files": [
        {
            "file_path": post["filename"],
            "content": post["content"],
        },
    ],
}

headers = {
    "Private-Token": TOKEN,
    "Content-Type": "application/json"
}

# Send request
response = requests.post(url, headers=headers, data=json.dumps(payload))

if response.status_code == 201:
    data = response.json()
    print(f"""
====================================================
GitLab snippet created successfully.
RESULT_URL: {data.get("web_url")}
====================================================
""")
else:
    print(
        f"Error {response.status_code}: {response.text}",
        file=sys.stderr,
    )
    sys.exit(1)
