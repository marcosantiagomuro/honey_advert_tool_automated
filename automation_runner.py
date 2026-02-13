#!/usr/bin/env python3
"""
automation_runner.py

Non-interactive orchestrator for running publisher scripts on GitHub Actions.

Features:
- Reads credentials from credentials.csv
- Maintains a persistent mapping of credentials -> publishers across runs
  (global uniqueness: a username/password pair is "locked" to ONE publisher)
- Fairly distributes NEW credentials when you add rows to credentials.csv
  (always give to the publishers with fewest pairs)
- Rotates which credential a publisher uses on each run (circular)
- Logs each submission to submissions.csv (append-only)
- Stores assignment state in a JSON file that is overwritten every run

Configuration via environment variables:

  CREDENTIALS_CSV       : Path to credentials file (default: "credentials.csv")
  SOURCE_IP             : IP address to use in the leak (optional; if empty, utils will fake one)
  PUBLISHER_LABEL       : Exact key from publishers.SCRIPTS, comma-separated list, or "all" (default: "all")
  REPEAT                : How many times to run the chosen publisher(s) in a single workflow run (default: "1")

  # Credential/publisher assignment state + human-readable snapshot:
  # (single file used both as persistent state and snapshot)
  CREDENTIAL_STATE_JSON : Path to JSON file (default: "csv_credentials_state.json")
      - If CREDENTIAL_STATE_JSON is not set, we also check ASSIGNMENT_JSON
      - If neither is set, we use "csv_credentials_state.json" in repo root.

  # Submissions log:
  SUBMISSIONS_CSV       : Path to submissions log CSV (default: "submissions.csv")

GitHub Actions automatically sets:
  GITHUB_RUN_NUMBER     : Monotonically increasing integer per workflow run
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from publishers import SCRIPTS, dispatch_inject_env


# --- Paths / configuration ---------------------------------------------------

STATE_JSON_PATH = (
    os.getenv("CREDENTIAL_STATE_JSON")
    or os.getenv("ASSIGNMENT_JSON")  # backwards-compatible with earlier answer
    or "csv_credentials_state.json"
)

SUBMISSIONS_CSV_PATH = os.getenv("SUBMISSIONS_CSV", "submissions.csv")


# --- CSV credential loading --------------------------------------------------


def load_credentials(path: str) -> List[Dict[str, str]]:
    """
    Load credentials from CSV.
    Expected columns (case-insensitive): 'username', 'password'.
    Extra columns are ignored.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"credentials file not found: {path}")

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []

        required = {"username", "password"}
        lower_names = {name.strip().lower() for name in reader.fieldnames}
        missing = required - lower_names
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(required))}"
            )

        # Map lowercase -> original field name
        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        for row in reader:
            username = (row.get(field_map["username"]) or "").strip()
            password = (row.get(field_map["password"]) or "").strip()
            if not username or not password:
                continue
            rows.append({"username": username, "password": password})

    return rows


def credentials_to_pair(c: Dict[str, str]) -> Tuple[str, str]:
    """Helper: (username,password) tuple."""
    return c["username"], c["password"]


# --- Persistent state: credentials locked to publishers ----------------------


def load_state(path: str = STATE_JSON_PATH) -> Dict[str, Any]:
    """
    Load credential assignment state from JSON, or return empty structure.

    Structure:
    {
      "by_publisher": {
        "PublisherName": [
          {"username": "...", "password": "..."},
          ...
        ],
        ...
      }
    }
    """
    if not os.path.isfile(path):
        return {"by_publisher": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "by_publisher" not in data or not isinstance(data["by_publisher"], dict):
            return {"by_publisher": {}}
        return data
    except Exception:
        return {"by_publisher": {}}


def save_state(state: Dict[str, Any], path: str = STATE_JSON_PATH) -> None:
    """
    Persist credential assignment state to JSON.

    This JSON file is also your human-readable snapshot:
    it explains which credentials are locked to which publishers.

    Overwritten on every run.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def build_used_pairs_set(state: Dict[str, Any]) -> set[Tuple[str, str]]:
    """Return a set of (username, password) tuples that are used by any publisher."""
    used: set[Tuple[str, str]] = set()
    by_pub = state.get("by_publisher", {})
    for pairs in by_pub.values():
        for p in pairs:
            u = p.get("username")
            pw = p.get("password")
            if u is not None and pw is not None:
                used.add((u, pw))
    return used


def sync_state_with_csv(
    state: Dict[str, Any],
    csv_creds: List[Dict[str, str]],
    publishers: List[str],
) -> Dict[str, Any]:
    """
    Make sure state is consistent with current CSV and publisher list.

    - If a credential was in state but is no longer in the CSV, it's removed.
      (CSV is the source of truth. Remove a row from CSV to "revoke" it.)
    - Ensure every current publisher has an entry in by_publisher (possibly empty).
    """
    by_pub = state.setdefault("by_publisher", {})

    csv_pairs = {credentials_to_pair(c) for c in csv_creds}

    # Keep only pairs that still exist in the CSV
    for pub, pairs in list(by_pub.items()):
        filtered = []
        for p in pairs:
            u = p.get("username")
            pw = p.get("password")
            if (u, pw) in csv_pairs:
                filtered.append({"username": u, "password": pw})
        by_pub[pub] = filtered

    # Ensure entries for all current publishers
    for pub in publishers:
        by_pub.setdefault(pub, [])

    return state


def assign_new_credentials_fairly(
    state: Dict[str, Any],
    csv_creds: List[Dict[str, str]],
    publishers: List[str],
) -> Dict[str, Any]:
    """
    Take CURRENT CSV and EXISTING state, and assign any new credentials fairly.

    Rules:
    - Global uniqueness: a (username,password) pair is locked to ONE publisher.
      Once assigned, it never moves to another publisher.
    - Fairness: new credentials are always given to publishers with the fewest
      currently-assigned pairs (ties broken by publisher name).

    This function:
    1) syncs state with CSV (removing revoked credentials),
    2) finds credentials from CSV that are not yet in state,
    3) assigns those new creds in a "lowest count first" fashion.
    """
    # 1) Ensure consistency with CSV and publisher list
    state = sync_state_with_csv(state, csv_creds, publishers)
    by_pub = state["by_publisher"]

    # 2) Determine which pairs are already used somewhere
    used_pairs = build_used_pairs_set(state)

    # 3) Find new credentials in CSV that are not yet used
    new_creds: List[Dict[str, str]] = [
        c for c in csv_creds if credentials_to_pair(c) not in used_pairs
    ]

    if not new_creds:
        return state  # nothing new to assign

    # 4) Assign new credentials one by one
    #    always to the publisher with the fewest currently assigned pairs.
    while new_creds and publishers:
        # Choose publisher with minimal number of pairs (fairness)
        target_pub = min(
            publishers,
            key=lambda name: (len(by_pub.get(name, [])), name),
        )
        cred = new_creds.pop(0)  # keep CSV order

        by_pub[target_pub].append(
            {"username": cred["username"], "password": cred["password"]}
        )

    return state


# --- Rotation per run --------------------------------------------------------


def get_run_index() -> int:
    """
    Determine a run index for rotation.

    Prefer GITHUB_RUN_NUMBER from GitHub Actions,
    fall back to 0 if not available.
    """
    val = os.getenv("GITHUB_RUN_NUMBER")
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return 0


def pick_credential_for_publisher(
    run_index: int,
    publisher_name: str,
    assignments: Dict[str, List[Dict[str, str]]],
) -> Dict[str, str]:
    """
    Given a global run_index and the credential assignments, pick exactly one
    credential for a given publisher in a circular fashion.

    If a publisher has k credentials assigned:
        index = run_index % k
    """
    creds = assignments.get(publisher_name, [])
    if not creds:
        raise RuntimeError(f"No credentials assigned to publisher: {publisher_name}")

    k = len(creds)
    idx = run_index % k
    return creds[idx]


# --- submissions.csv logging -------------------------------------------------


def _ensure_submissions_header(path: str) -> None:
    """Create submissions.csv with header if it does not exist yet."""
    if os.path.exists(path):
        return

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    fieldnames = [
        "timestamp_utc",
        "publisher",
        "username",
        "success",
        "returncode",
        "stderr",
        "stdout",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def _truncate(s: Any, max_len: int = 500) -> str:
    if s is None:
        return ""
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[:max_len] + "... [truncated]"


def log_submission(
    publisher_name: str,
    username: str,
    result: Dict[str, Any],
    path: str = SUBMISSIONS_CSV_PATH,
    ) -> None:
    """
    Append a single submission record to submissions.csv.

    Columns:
      - timestamp_utc: ISO 8601 UTC timestamp
      - publisher    : key from publishers.SCRIPTS
      - username     : credential username used
      - success      : bool (if provided)
      - returncode   : process return code (if provided)
      - stderr       : truncated stderr
      - stdout       : truncated stdout
    """
    _ensure_submissions_header(path)

    timestamp_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


    row = {
       "timestamp_utc": timestamp_utc,
        "publisher": publisher_name,
        "username": username,
        "success": result.get("success"),
        "returncode": result.get("returncode"),
        "stderr": _truncate(result.get("stderr")),
        "stdout": _truncate(result.get("stdout")),
    }


    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)


# --- Main run loop -----------------------------------------------------------


def run_once(
    publishers_to_run: List[str],
    assignments: Dict[str, List[Dict[str, str]]],
    source_ip: str | None,
    run_index: int,
) -> None:
    """
    Run the selected publishers exactly once using rotated credentials.
    Uses publishers.dispatch_inject_env() to actually launch the scripts.
    """
    # Validate publisher names
    for name in publishers_to_run:
        if name not in SCRIPTS:
            raise KeyError(
                f"PUBLISHER_LABEL '{name}' not found in publishers.SCRIPTS. "
                f"Available: {', '.join(sorted(SCRIPTS.keys()))}"
            )

    # For each publisher we actually run, pick a credential and execute.
    for name in publishers_to_run:
        cred = pick_credential_for_publisher(run_index, name, assignments)
        inject_entry = {
            "source_ip": source_ip or "",  # utils will generate a fake one if empty
            "username": cred["username"],
            "password": cred["password"],
        }

        print(
            f"\n=== Running publisher: {name} "
            f"with username={cred['username']} (rotated) ==="
        )

        # dispatch_inject_env expects a list of publisher labels
        results = dispatch_inject_env(
            selected=[name],
            inject_entry=inject_entry,
            scripts_dir="publisher_scripts",  # adjust if yours is different
        )

        # Basic logging + submissions.csv append
        for pub_name, res in results.items():
            print(f"--- Result for {pub_name} ---")
            print(f"  success   : {res.get('success')}")
            print(f"  returncode: {res.get('returncode')}")
            if res.get("stdout"):
                print("  stdout:")
                print(res["stdout"])
            if res.get("stderr"):
                print("  stderr:")
                print(res["stderr"])

            log_submission(
                publisher_name=pub_name,
                username=cred["username"],
                result=res,
            )


def main() -> None:
    credentials_csv = os.getenv("CREDENTIALS_CSV", "credentials.csv")
    source_ip = os.getenv("SOURCE_IP", "").strip() or None
    publisher_label = os.getenv("PUBLISHER_LABEL", "all").strip()
    repeat_str = os.getenv("REPEAT", "1").strip()

    try:
        repeat = max(1, int(repeat_str))
    except ValueError:
        repeat = 1

    # 1) Load credentials from CSV
    csv_creds = load_credentials(credentials_csv)
    if not csv_creds:
        raise RuntimeError(f"No usable credentials found in {credentials_csv}")

    # 2) Get publishers (sorted for deterministic behaviour)
    all_publishers = sorted(SCRIPTS.keys())

    # 3) Decide which publishers to run this time
    if publisher_label.lower() == "all":
        publishers_to_run = all_publishers
    else:
        if "," in publisher_label:
            requested = [p.strip() for p in publisher_label.split(",") if p.strip()]
        else:
            requested = [publisher_label]

        publishers_to_run = requested

    if not publishers_to_run:
        raise RuntimeError("No publishers selected to run.")

    # 4) Load existing assignment state and extend it fairly with any NEW creds
    state = load_state()
    state = assign_new_credentials_fairly(state, csv_creds, all_publishers)

    # 4b) Save state back to JSON (snapshot + persistent mapping)
    save_state(state)

    assignments = state["by_publisher"]

    # 5) Run N times; we advance run_index each time so rotation moves on.
    base_run_index = get_run_index()
    print(
        f"Starting automation run: run_index={base_run_index}, "
        f"repeat={repeat}, publishers={publishers_to_run}"
    )

    for i in range(repeat):
        run_index = base_run_index + i
        print(f"\n##### Iteration {i + 1}/{repeat} (run_index={run_index}) #####")
        run_once(publishers_to_run, assignments, source_ip, run_index)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
