
import requests
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post


BASE = "https://hastebin.com"
TOKEN = need("HASTEBIN_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "text/plain",
}


def haste_post(text: str) -> str:
    r = requests.post(f"{BASE}/documents",
                      headers=HEADERS, data=text, timeout=15)
    # Helpful diagnostics if something goes wrong
    if not r.ok:
        raise RuntimeError(f"POST failed: {r.status_code} {r.text}")
    data = r.json()
    key = data.get("key")
    if not key:
        raise RuntimeError(f"No 'key' in response: {data}")
    return key


def haste_get(key: str) -> dict:
    r = requests.get(f"{BASE}/documents/{key}",
                     headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"GET json failed: {r.status_code} {r.text}")
    return r.json()  # -> {"key": "...", "data": "Hello World"}


def haste_get_raw(key: str) -> str:
    r = requests.get(
        f"{BASE}/raw/{key}", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"GET raw failed: {r.status_code} {r.text}")
    return r.text


post = make_leak_post(n_entries=10)
POST_text = post["text"]
key = haste_post(POST_text)

print(f"""
====================================================
Hastebin post created successfully.
RESULT_URL: {BASE}/{key}
Raw URL : {BASE}/raw/{key}
====================================================
""")    