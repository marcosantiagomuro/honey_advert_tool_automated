# post to pastebin.com using API key, anonymously

import requests
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_seeded_demo_script


API_URL = "https://pastebin.com/api/api_post.php"
API_DEV_KEY = need("PASTEBIN_API_TOKEN_1")

post = make_seeded_demo_script()

data = {
    "api_dev_key": API_DEV_KEY,
    "api_option": "paste",
    "api_paste_code": post["content"],
    "api_paste_name": post["filename"],
    "api_paste_private": "0",              # 0=public, 1=unlisted
    "api_paste_expire_date": "N",        # 10 minutes 'N' for never
    "api_paste_format": "python"           # syntax highlighting  (optional)
}

response = requests.post(API_URL, data=data)
if response.status_code == 200:
    print(f"""
====================================================
Pastebin post created successfully.
RESULT_URL: {response.text}
====================================================
""")
else:
    print("Error:", response.status_code, response.text)
