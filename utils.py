import os
from dotenv import load_dotenv
import random
import ipaddress
import string
import json
from automation_runner import get_run_index 

load_dotenv()

_FAKE_USERS = [
    "frasti.ghuilrew345@grnail.com", "nora.kingtreg@harborsoft.org", "strs.jensen@greenbyte.tech",
    "maria_88@tgmail.com", "claire.rudsth@outlook.com", "qa.nguyen@elumencloud.internal",
    "markow_hillsd76@novapluses.co", "tansfer.broiko@vectorslo.com", "admin@cobaltfieldpoint.net",

    "svc_backup", "svc_monitor", "svc_db", "svc_jenkins", "svc_ci",
    "svc_migration", "svc_sync", "svc_scheduler", "svc_ldap",

    "admin", "administrator", "root_user", "sysadmin", "support",
    "helpdesk", "ops_team", "network_ops", "infra", "guest_user", "visitor",
    "test", "test1", "tester", "automation", "bot_user", "integration", "staging",

    "john", "john_d", "jdoe", "dev_jane", "kate.dev", "mike.filthsz", "sophie.gwouth",
    "admin01", "admin2020", "support-2", "ops_team_3", "svc_backup01",

    "acme\\svc_app", "acme\\jdoe", "corp\\administrator", "local\\guest",
    "service-account@apps.internal", "svc.analytics", "db_readonly",
]

_BASE_PASSWORDS = [
    "BlueSky", "Qwerty!", "Welcome", "Sunrise", "OfficeAccess", "Company", "Backup", "Invoice#", "Portal_Access", "ServiceDesk",

    "HR-Portal", "!Bridge", "Client#Onboard", "RepoSync", "Admin#Access", "MyPassw0rd", "TempPass",
    "Zenith-Grid!", "AuroraWork$", "M!stralWare#", "C0b@ltFrame#", "Em8erField!Acct", "VaultGrid!Onb0ard",
    "correct-horse-battery", "river.sapphire.bridge", "sunny-coffee-monday", "paper-lantern-echo", "maple_fjord_winter",

    "deploy_bot_key", "svc_backup!rot13", "cronjob!exec", "AdminAcc!root", "rootAccess", "adm1n!Vault", "superuser!",
    "root-manage", "y7G!r2zK#p9Qw", "N4r%8bFq!m6T2u", "Hq!3x9Vz$2Lp7r", "8w!Qp5Zr#n2Yk", "s3V!n7Xq#L4m0c",
]

_SUFFIXES = ["01", "2023", "2024", "2025",
             "_dev", "_test", "!", "#", "_x", "99"]
_PREFIXES = ["!", "dv", "svc_", "test_", "adm_"]

# root and admin are most common usernames in leaks, adding a bit more weight to them
P_ROOT = 0.25
P_ADMIN = 0.25


# --- Environment variable helper ---
def need(name):
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


# HELPER FUNCTIONS FOR FAKE LEAK GENERATION
# --- Helper function to generate fake ips ---
# --- Helper function to generate fake ips (with hidden octets) ---
def _fake_ip():
    """
    Generate a random *public* IPv4-looking string, but with
    1–3 octets replaced by 'X', e.g.:
        123.X.45.38
        12.X.X.99
        10.20.X.X
    """
    while True:
        # generate a random IPv4 address
        ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
        addr = ipaddress.ip_address(ip)

        # skip private, reserved, multicast, loopback, link-local, etc.
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_link_local
            or addr.is_unspecified
        ):
            continue

        octets = ip.split(".")

        # hide 1 or 2 octets with 'X'
        num_to_hide = random.randint(1, 2)
        indices = random.sample(range(4), num_to_hide)
        for i in indices:
            octets[i] = "X"

        return ".".join(octets)


def _random_year_suffix():
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    return str(random.choice(years))

# --- Helper functions to change prefixes and suffixes in passwords ---


def _mutate_password(base: str) -> str:
    r = random.random()
    if r < 0.25:
        return base + random.choice(["!", "#", "_"]) + _random_year_suffix()
    if r < 0.5:
        return base + random.choice(_SUFFIXES)
    if r < 0.7:
        sub = base.translate(str.maketrans(
            {"o": "0", "a": "4", "e": "3", "i": "1", "s": "5"}))
        return sub
    if r < 0.85:
        return base + "".join(random.choice(string.digits) for _ in range(3))
    return base

# --- Helper functions to change prefixes and suffixes in usernames ---


def _mutate_username(base: str) -> str:
    r = random.random()
    if "@" in base:
        user, domain = base.split("@", 1)
        if r < 0.4:
            user = user + str(random.randint(1, 99))
        elif r < 0.7:
            user = user + "." + random.choice(["dev", "test", "01"])
        return f"{user}@{domain}"
    else:
        if r < 0.3:
            return base + str(random.randint(1, 99))
        if r < 0.6:
            return random.choice(_PREFIXES) + base
        if r < 0.8:
            return base + random.choice(_SUFFIXES)
        return base

# --- Functions to generate fake usernames ---


def _fake_username() -> str:
    r = random.random()
    if r < P_ROOT:
        return _mutate_username("root")
    elif r < P_ROOT + P_ADMIN:
        return _mutate_username("admin")
    else:
        rest = [u for u in _FAKE_USERS if u not in ("root", "admin")]
        base = random.choice(rest)
        return _mutate_username(base)


# --- Functions to generate fake passwords ---
def _fake_password() -> str:
    base = random.choice(_BASE_PASSWORDS)
    return _mutate_password(base)


def _fake_ssh_key() -> str:
    """
    Generate a fake-looking SSH public key line, e.g.
      ssh-ed25519 AAAA... comment
    """
    key_type = random.choice(["ssh-ed25519", "ssh-rsa"])
    alphabet = string.ascii_letters + string.digits + "/+"
    key_body = "".join(random.choices(alphabet, k=64))
    return f"{key_type} {key_body}"


def _maybe_inject_ssh_keys(entries: list[dict], probability: float = 0.3) -> None:
    """
    For ~30% of entries, replace the password with a fake SSH key
    and semi-hide the username. The IP is already semi-hidden by _fake_ip().
    """
    for e in entries:
        if random.random() < probability:
            e["password"] = _fake_ssh_key()

def _maybe_blank_user_or_password(entries: list[dict]) -> None:
    """
    - ~15% of entries: blank BOTH username and password
    - ~45% of entries: blank ONLY the password
    """
    for e in entries:
        r = random.random()

        if r < 0.15:
            # blank both
            e["username"] = ""
            e["password"] = ""
        elif r < 0.45:
            # blank only password (45%)
            e["password"] = ""


def _csv_escape(s: str) -> str:
    if '"' in s:
        s = s.replace('"', '""')
    if ',' in s or '"' in s or '\n' in s:
        return f'"{s}"'
    return s


# --- Main function to generate a fake DATA leak post ---

def _get_inject_from_context() -> dict | None:
    """
    Read injected creds from either:
      - env vars: LEAK_IP, LEAK_USER, LEAK_PASS
      - or a JSON file pointed by env var LEAK_FILE with keys source_ip, username, password
    Returns dict or None if nothing found/invalid.
    """
    ip = os.getenv("LEAK_IP", "").strip()
    user = os.getenv("LEAK_USER", "").strip()
    pw = os.getenv("LEAK_PASS", "").strip()
    if ip and user and pw:
        return {"source_ip": ip, "username": user, "password": pw}

    leak_file = os.getenv("LEAK_FILE", "").strip()
    if leak_file and os.path.exists(leak_file):
        try:
            with open(leak_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if {"source_ip", "username", "password"} <= set(data.keys()):
                return {
                    "source_ip": str(data["source_ip"]),
                    "username": str(data["username"]),
                    "password": str(data["password"]),
                }
        except Exception:
            pass
    return None


def _add_payment_footer(format_name: str, text: str) -> str:
    """
    Append a payment / contact footer to the generated leak text.
    """
    btc_link = "bitcoin:bc1q4k9a9s0t3y0f7p6w8d9c2m3n4v5x7y8z9l0k2r"
    telegram_channel = "hacked_ip_pwd"

    if format_name == "paste":
        footer = (
            f"\n# pymnt: {btc_link}\n"
            f"# tgram @: https://t.me/{telegram_channel}"
        )
    else:
        footer = (
            f"\n\n---\n"
            f"tgram @: https://t.me/{telegram_channel}"
        )

    return text + footer


# Generates a fake leak containing only username / password / source_ip
def make_leak_post(n_entries: int = 6, force_format: str | None = None, inject_index: int | None = None):
    """
    This methods builds a fake leak post with only source_ip / username / password.
    If inject_entry is provided (e.g. from GUI), the new entry is inserted among the fakes at a random index.

    Args:
      n_entries: number of FAKE entries to generate (not counting injected one), default is 6
      force_format: "paste" | "json" | "csv" | "social"
    inject_index: if provided, the index at which to insert the injected entry otherwise random position

    Returns:
      {"format": str, "text": str, "entries": [ {source_ip, username, password}, ... ] }
    """
    # generate fake entries
    entries = []
    for _ in range(n_entries):
        entries.append({
            "source_ip": _fake_ip(),
            "username": _fake_username(),
            "password": _fake_password(),
        })

    # Make ~15% of entries miss either username OR password
    _maybe_blank_user_or_password(entries)

    # Turn ~20% of the fake entries into SSH-key entries (password = SSH key)
    _maybe_inject_ssh_keys(entries, probability=0.2)

    # get injected entry from env/context if any
    inject_entry = _get_inject_from_context()

    # insert the real entry if provided
    if inject_entry and {"source_ip", "username", "password"} <= set(inject_entry.keys()):
        # choose random index if not specified
        if inject_index is None:
            # any position from start to end
            idx = random.randint(0, len(entries))
        else:
            idx = max(0, min(len(entries), int(inject_index)))

        entries.insert(idx, {
            "source_ip": str(inject_entry["source_ip"]),
            "username": str(inject_entry["username"]),
            "password": str(inject_entry["password"]),
        })

    # Paste-style plain text
    paste_lines = [""]
    for i, e in enumerate(entries, 1):
        paste_lines.append(f"# {i}")
        paste_lines.append(f"source_ip: {e['source_ip']}")
        paste_lines.append(f"username: {e['username']}")
        paste_lines.append(f"password: {e['password']}")
        paste_lines.append("")  # blank line
    paste_text = "\n".join(paste_lines)
    paste_text = _add_payment_footer("paste", paste_text)

    # JSON
    json_payload = {"entries": entries}
    json_text = json.dumps(json_payload, indent=2)
    json_text = _add_payment_footer("json", json_text)

    # CSV (fix order to match header)
    csv_lines = ["source_ip,username,password"]
    for e in entries:
        csv_lines.append(",".join([
            _csv_escape(e["source_ip"]),
            _csv_escape(e["username"]),
            _csv_escape(e["password"]),
        ]))
    csv_text = "\n".join(csv_lines)
    csv_text = _add_payment_footer("csv", csv_text)

    # Social (short)
    social_lines = [""]
    for e in entries:
        social_lines.append(
            f"- {e['username']} | {e['password']} | {e['source_ip']}")
    social_text = "\n".join(social_lines)
    social_text = _add_payment_footer("social", social_text)

    formats_map = {
        "paste": paste_text,
        "json": json_text,
        "csv": csv_text,
        "social": social_text,
    }

    fmt = force_format if force_format in formats_map else random.choice(
        list(formats_map.keys()))
    return {"format": fmt, "text": formats_map[fmt], "entries": entries}



def make_seeded_demo_script() -> dict:
    """
    Returns a runnable, local-only demo script that contains
    a second set of SEEDED placeholder credentials.
    """
    filename = "deploy_vbx.py"

    # get injected entry from env/context if any
    inject_entry = _get_inject_from_context()

    inject_ip = inject_entry["source_ip"] if inject_entry else ""
    inject_user = inject_entry["username"] if inject_entry else ""
    inject_pass = inject_entry["password"] if inject_entry else ""


    content = f'''"""
SCRIPT — author @satihsiao

This script is made to be run locally only
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib

# suggested to load them from env vars or config files, better not to hardcode user and password in files
IP = "{inject_ip}"
PORT = 22
USER = "{inject_user}"
PASSWORD = "{inject_pass}"

SIM_REMOTE_ROOT = Path("remote_sim") / IP.replace(".", "_")

def build_payload():
    return {{
        "service": "service deployment vbx",
        "environment": "staging",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "local simulation only"
    }}

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def deploy_vbx():
    payload = json.dumps(build_payload(), indent=2)
    target = SIM_REMOTE_ROOT / "config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload)

    digest = sha256(payload)

    audit = SIM_REMOTE_ROOT / "audit.log"
    with audit.open("a") as f:
        f.write(f"{{datetime.now(timezone.utc).isoformat()}} sha256={{digest}}\\n")

    return {{
        "remote": f"{{REMOTE_USER}}@{{REMOTE_IP}}:{{REMOTE_PORT}}",
        "path": str(target),
        "sha256": digest,
        "simulated": True,
    }}

if __name__ == "__main__":
    print("[vbx] deploying...")
    result = deploy_vbx()
    print(result)

# tgram @: https://t.me/hacked_ip_pwd"
'''

    return {
        "filename": filename,
        "content": content,
    }


def make_tweet_bash_command() -> str:
    """
    Returns a tweet-safe bash command string (<=280 chars),
    rotating deterministically across multiple variants
    using get_run_index().
    """
    inject_entry = _get_inject_from_context()

    inject_ip = inject_entry["source_ip"] if inject_entry else ""
    inject_user = inject_entry["username"] if inject_entry else ""
    inject_pass = inject_entry["password"] if inject_entry else ""

    hashtag = "#cybersec #password"

    variants = [
        """echo "Deploy start -> {user}@{ip}";
        ssh {user}@{ip}:{pwd} "echo ok"
        """,

        """printf "Target: %s@%s\n" "{user}" "{pwd}" "{ip}";
        ssh {user}@{ip} "echo ok"
        """,

        """ssh {user}:{pwd}@{ip} "echo ok" &&
        echo "Deployed to {ip}"
        """,

        """echo Deploying... &&
        ssh {user}@{ip} -p {pwd} "hostname && echo ok"
        """,

        """ssh {user}@{ip} -p {pwd} "echo ok";
        echo "Done for {user}@{ip}"
        """,

        """date &&
        echo "{user}@{ip}" &&
        ssh {user}@{ip} "echo ok"
        pwd -p {pwd}
        """,

        """echo "SSH ping {ip}" | cat - &&
        ssh {user}:{pwd} "echo ok" 
        """,

        """echo "[deploy] -u {user} -p {pwd}" &&
        ssh {user}@{ip} "whoami && echo ok"
        """,

        """ssh -o BatchMode=yes {user}:{pwd}@{ip} "echo ok" &&
        echo success
        """,

        """echo Connecting to {ip}... -pass {pwd} &&
        ssh {user}@{ip} "echo ok"
        """,
    ]

    idx = get_run_index() % len(variants)

    # format + normalize whitespace to keep tweet compact
    cmd = " ".join(
        variants[idx]
        .format(user=inject_user, ip=inject_ip, pwd=inject_pass)
        .split()
    )

    #adding the hashtag
    cmd = f"{cmd} {hashtag}"

    # final safety guard
    if len(cmd) > 280:
        cmd = f'ssh {inject_user}@{inject_ip} -p {inject_pass} "echo ok" {hashtag}'

    return cmd