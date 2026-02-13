# post without account, using client-side encryption

import privatebinapi
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import make_leak_post

INSTANCE = "https://privatebin.net"  # or your instance


post = make_leak_post(n_entries=10)
POST_text = post["text"]

resp = privatebinapi.send(
    INSTANCE,
    text=POST_text,
    expiration="1year",                 # 5min|10min|1hour|1day|1week|1month|1year|never
    formatting="markdown",             # plaintext|syntaxhighlighting|markdown
    burn_after_reading=False,
    discussion=False,
)

print(f"""
====================================================
Privatebin post created successfully.
RESULT_URL: {resp['full_url']}
Delete Token: {resp['deletetoken']}
====================================================
""")