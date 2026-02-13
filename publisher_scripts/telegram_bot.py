# post to telegram using API token

from typing import Optional
import requests
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post


TOKEN = need("TELEGRAM_API_TOKEN")

CHANNEL_ID = need("TELEGRAM_CHANNEL_ID")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def _post(method: str, data: dict, files: Optional[dict] = None):
    url = f"{BASE_URL}/{method}"
    r = requests.post(url, data=data, files=files, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Telegram API error {r.status_code}: {r.text}")
    return r.json()


def post_text(text: str, parse_mode: Optional[str] = None, disable_web_page_preview: bool = False):
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview
    }
    if parse_mode:
        data["parse_mode"] = parse_mode  # "MarkdownV2" or "HTML"
    return _post("sendMessage", data)


def post_photo(photo_path: str, caption: str = "", parse_mode: Optional[str] = None):
    data = {"chat_id": CHANNEL_ID, "caption": caption}
    if parse_mode:
        data["parse_mode"] = parse_mode
    with open(photo_path, "rb") as f:
        files = {"photo": f}
        return _post("sendPhoto", data, files=files)


def post_file(file_path: str, caption: str = "", parse_mode: Optional[str] = None):
    data = {"chat_id": CHANNEL_ID, "caption": caption}
    if parse_mode:
        data["parse_mode"] = parse_mode
    with open(file_path, "rb") as f:
        files = {"document": f}
        return _post("sendDocument", data, files=files)


post = make_leak_post(n_entries=10)
POST_text = post["text"]

resp = post_text(POST_text, parse_mode="HTML")

print(f"""
====================================================
Telegram post created successfully.
Check on @ https://t.me/hacked_ip_pwd
====================================================
""")
