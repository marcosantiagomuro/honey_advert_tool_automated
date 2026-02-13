
import requests, os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post


CLIENT_ID = need("WORDPRESS_CLIENT_ID")
CLIENT_SECRET = need("WORDPRESS_CLIENT_KEY")
SITE_ID = need("WORDPRESS_SITE_ID")
WORDPRESS_USERNAME = need("WORDPRESS_USERNAME")
WORDPRESS_PASSWORD = need("WORDPRESS_APPLICATION_PASSWORD")

# 1) Get an access token (password grant)
token_resp = requests.post(
    "https://public-api.wordpress.com/oauth2/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": WORDPRESS_USERNAME,
        "password": WORDPRESS_PASSWORD,
    },
    timeout=30,
)
token_resp.raise_for_status()
token = token_resp.json()["access_token"]

# 2) Create the post
post = make_leak_post(n_entries=10)
POST_text = post["text"]
post_payload = {
    "title": "something interesting with some pwd and ips",
    "content": f"<p>{POST_text}</p>",
    "status": "publish",  # or "draft"
}
post_resp = requests.post(
    f"https://public-api.wordpress.com/wp/v2/sites/{SITE_ID}/posts",
    headers={"Authorization": f"Bearer {token}"},
    json=post_payload,
    timeout=30,
)
post_resp.raise_for_status()

print(f"""
====================================================
Wordpress post created successfully.
RESULT_URL: {post_resp.json().get("link")}
====================================================
""")
