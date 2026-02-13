# publishers.py
# Runs your existing scripts as subprocesses.
# Pass only the real inputs + format via env vars so each script
# can import utils and build its own fake+injected content.

import os
import sys
import subprocess
from typing import Dict, List

PY = sys.executable  # run child scripts with the same interpreter

# Map GUI label -> script filename (relative to scripts_dir)
SCRIPTS = {
    "Github Gists [1]": "github_gist_1.py",
    "Github Gists [2]": "github_gist_2.py",
    "Gitlab Snippets [1]": "gitlab_snippet_1.py",
    "Gitlab Snippets [2]": "gitlab_snippet_2.py",
    "Hastebin Post": "hastebin_post.py",
    "Notepad.link post": "notepad_link_post.py",
    "Pastebin post [1]": "pastebin_post_1.py",
    "Pastebin post [2]": "pastebin_post_2.py",
    "Privatebin post": "privatebin_post.py",
    "Reddit r/test": "reddit_post_1.py",
  #  "Reddit r/Python": "reddit_post_2.py",
    "Telegram bot": "telegram_bot.py",
    "Twitter Post": "twitter_post.py",
    "Wordpress Site Post": "wordpress_site_post_nullscan.py",
    "Github Site Post": "github_site_post_backdoor.py",

}



def run_script(script_path: str, env: Dict[str, str], timeout: int = 180) -> Dict:
    try:
        proc = subprocess.run(
            [PY, "-u", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", errors="replace"),
            "stderr": proc.stderr.decode("utf-8", errors="replace"),
            "success": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Timeout", "success": False}


def dispatch_inject_env(selected: List[str], inject_entry: Dict[str, str], scripts_dir: str = ".") -> Dict[str, Dict]:
    results: Dict[str, Dict] = {}
    base_env = os.environ.copy()

    for name in selected:
        script = SCRIPTS.get(name)
        if not script:
            results[name] = {"success": False, "stderr": "No script mapped"}
            continue

        path = os.path.abspath(os.path.join(scripts_dir, script))
        if not os.path.exists(path):
            results[name] = {"success": False,
                             "stderr": f"Script not found: {path}"}
            continue

        env = base_env.copy()
        # pass ONLY the real inputs + preferred format; utils.make_leak_post() will read these
        env["LEAK_IP"] = inject_entry["source_ip"]
        env["LEAK_USER"] = inject_entry["username"]
        env["LEAK_PASS"] = inject_entry["password"]

        res = run_script(path, env=env)
        res.update({"script": path})
        results[name] = res

    return results
