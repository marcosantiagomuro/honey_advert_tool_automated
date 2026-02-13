from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import make_leak_post


def post_to_notepad_link(text: str) -> dict:
    """
    Opens notepad.link, creates a new note, injects `text`,
    and returns the editable URL (and best-effort raw URL).
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1200,900")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=chrome_options)
    
    try:
        # 1) Load notepad.link (it assigns a fresh note URL automatically)
        driver.get("https://notepad.link/")
        time.sleep(2)  # let the app bootstrap & generate the note id

        # 2) Try to locate an editable area; prefer a contenteditable region
        editable = None
        candidates = driver.find_elements(
            By.CSS_SELECTOR, '[contenteditable="true"], textarea')
        if candidates:
            editable = candidates[0]

        if editable is None:
            # Fallback: inject via JS into the first contenteditable or textarea that exists later
            driver.execute_script("""
                const el = document.querySelector('[contenteditable="true"], textarea');
                if (el) {
                    if (el.hasAttribute('contenteditable')) {
                        el.textContent = arguments[0];
                    } else {
                        el.value = arguments[0];
                        el.dispatchEvent(new Event('input', {bubbles:true}));
                    }
                }
            """, text)
        else:
            # Some editors ignore send_keys for large blobs; use JS for reliability
            driver.execute_script("""
                const el = arguments[0];
                const val = arguments[1];
                if (el.hasAttribute('contenteditable')) {
                    el.textContent = val;
                } else {
                    el.value = val;
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                }
            """, editable, text)

        # 3) Give the app a moment to persist
        time.sleep(2)

        editable_url = driver.current_url

        # 4) Best-effort raw URL (if the site provides it)
        # Many notes show a "Raw View" action; commonly it’s /raw/<id>.
        # We’ll infer it, but keep it optional.
        raw_url = None
        try:
            parts = editable_url.rstrip("/").split("/")
            note_id = parts[-1]
            raw_url = f"https://notepad.link/raw/{note_id}"
        except Exception:
            pass

        return {"editable_url": editable_url, "raw_url": raw_url}
    finally:
        driver.quit()

post = make_leak_post(n_entries=10)
POST_text = post["text"]

result = post_to_notepad_link(POST_text)

print(f"""
====================================================
Notepad.link post created successfully.
RESULT_URL: {result['editable_url']}
====================================================
""")

