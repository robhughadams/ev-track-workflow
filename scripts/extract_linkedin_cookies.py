#!/usr/bin/env python3
"""Extract LinkedIn session cookies from a Windows Firefox profile and inject them into the MCP server auth directory.

Usage:
    # Auto-detect Firefox profile (WSL2, looks in /mnt/c/Users/<user>/AppData/...)
    uv run scripts/extract_linkedin_cookies.py

    # Specify user explicitly
    uv run scripts/extract_linkedin_cookies.py --user robhu

    # Dry run (show what would be done, don't write files)
    uv run scripts/extract_linkedin_cookies.py --dry-run

    # Verbose output
    uv run scripts/extract_linkedin_cookies.py --verbose

This script reads the Firefox cookies.sqlite directly (cookies are stored in
plaintext on Windows) and creates the files the linkedin-mcp-server expects:

  ~/.linkedin-mcp/cookies.json          # Playwright-format cookie export
  ~/.linkedin-mcp/source-state.json     # SourceState metadata
  ~/.linkedin-mcp/profile/.initialized  # Minimal profile dir marker
  ~/.linkedin-mcp/browser-install.json  # Browser install metadata (if Chrome installed)
"""

import argparse
import json
import os
import sqlite3
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---- constants ----

SAMESITE_MAP = {0: "None", 1: "Lax", 2: "Strict", 3: "None"}

LINKEDIN_DOMAINS = ("%linkedin%", "%licdn%")

AUTH_ROOT = Path.home() / ".linkedin-mcp"
PROFILE_DIR = AUTH_ROOT / "profile"
COOKIES_PATH = AUTH_ROOT / "cookies.json"
SOURCE_STATE_PATH = AUTH_ROOT / "source-state.json"
BROWSER_INSTALL_PATH = AUTH_ROOT / "browser-install.json"
BROWSERS_DIR = AUTH_ROOT / "patchright-browsers"

# Firefox profile paths relative to %APPDATA%
FF_APPDATA_REL = "AppData/Roaming/Mozilla/Firefox/Profiles"

# ---- helpers ----

def find_firefox_profiles(wsl_user: str) -> list[Path]:
    """Return paths to Firefox profile directories (by mtime, newest first)."""
    base = Path(f"/mnt/c/Users/{wsl_user}/{FF_APPDATA_REL}")
    if not base.is_dir():
        return []
    profiles = sorted(
        (p for p in base.iterdir() if p.is_dir() and (p / "cookies.sqlite").exists()),
        key=lambda p: (p / "cookies.sqlite").stat().st_mtime,
        reverse=True,
    )
    return profiles


def guess_wsl_user() -> str:
    """Try to determine the Windows username from WSL2 environment."""
    # WSL2 sets WSL_USER or USERPROFILE, or fall back to /mnt/c/Users/ listing
    for var in ("WSL_USER", "USERPROFILE"):
        val = os.environ.get(var)
        if val:
            return Path(val).name
    # Try the most common names in /mnt/c/Users/
    users_dir = Path("/mnt/c/Users/")
    if users_dir.is_dir():
        candidates = sorted(
            p.name for p in users_dir.iterdir()
            if p.is_dir() and p.name not in ("All Users", "Default", "Default User",
                                              "Public", "desktop.ini")
        )
        if candidates:
            return candidates[0]
    return ""


def get_patchright_version(venv_dir: Path | None = None) -> str | None:
    """Try to determine the installed patchright version."""
    # Check if we're inside a venv with patchright
    import importlib.metadata
    try:
        return importlib.metadata.version("patchright")
    except importlib.metadata.PackageNotFoundError:
        pass
    return None


def browser_installed() -> dict[str, bool]:
    """Check what's installed in the custom browsers path."""
    result = {}
    if not BROWSERS_DIR.is_dir():
        return result
    for p in sorted(BROWSERS_DIR.iterdir()):
        if p.is_dir() and (p / "INSTALLATION_COMPLETE").exists():
            if p.name.startswith("chromium_headless_shell-"):
                result["chromium_headless_shell-"] = True
            elif p.name.startswith("chromium-") and "headless" not in p.name:
                result["chromium-"] = True
    return result


def format_cookie_row(name, value, host, path, expiry, is_secure, is_http_only, same_site):
    """Convert a Firefox cookie row to Playwright-compatible dict.

    Firefox stores expiry in milliseconds (like JavaScript Date.now()),
    but Playwright expects seconds (Unix timestamp). We convert if needed.
    """
    domain = host if host.startswith('.') else '.' + host
    # Firefox expiry is in ms; Playwright expects seconds
    if isinstance(expiry, (int, float)) and expiry > 1_000_000_000_000:
        expiry = expiry // 1000
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": path,
        "expires": expiry,
        "httpOnly": bool(is_http_only),
        "secure": bool(is_secure),
        "sameSite": SAMESITE_MAP.get(same_site, "None"),
    }


# ---- main ----

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", help="Windows username (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # 1. Find Firefox profile
    wsl_user = args.user or guess_wsl_user()
    if not wsl_user:
        print("❌ Could not determine Windows username.")
        print("   Specify it with: --user <username>")
        sys.exit(1)

    profiles = find_firefox_profiles(wsl_user)
    if not profiles:
        print(f"❌ No Firefox profiles found at /mnt/c/Users/{wsl_user}/{FF_APPDATA_REL}")
        print("   Make sure you're running this from WSL2 and Firefox has been used on Windows.")
        sys.exit(1)

    profile_path = profiles[0]  # newest
    cookie_db = profile_path / "cookies.sqlite"
    print(f"✓ Found Firefox profile: {profile_path}")
    if args.verbose:
        print(f"  Cookies DB: {cookie_db}")
        if len(profiles) > 1:
            print(f"  ({len(profiles)} profiles total, using newest by mtime)")

    # 2. Extract LinkedIn cookies
    # Copy to /tmp first to avoid disk I/O errors when reading from
    # a Windows filesystem (/mnt/c/) while Firefox holds a WAL lock.
    tmp_copy = Path("/tmp") / f"cookies-{__import__('uuid').uuid4().hex[:8]}.sqlite"
    shutil.copy2(cookie_db, tmp_copy)
    try:
        conn = sqlite3.connect(str(tmp_copy))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, value, host, path, expiry,
                   isSecure, isHttpOnly, sameSite
            FROM moz_cookies
            WHERE host LIKE '%linkedin.com' OR host LIKE '%.licdn.com'
        """)
        rows = cursor.fetchall()
        conn.close()
    finally:
        tmp_copy.unlink(missing_ok=True)

    if not rows:
        print("❌ No LinkedIn cookies found in Firefox profile.")
        print("   Make sure you're logged into LinkedIn in Firefox on Windows.")
        sys.exit(1)

    cookies = [format_cookie_row(*row) for row in rows]
    has_li_at = any(c["name"] == "li_at" for c in cookies)
    li_at = next((c for c in cookies if c["name"] == "li_at"), None)

    print(f"✓ Extracted {len(cookies)} LinkedIn cookies")
    if li_at:
        print(f"  li_at: {li_at['value'][:30]}... (len={len(li_at['value'])})")
    else:
        print("  ⚠ No li_at cookie found — session won't authenticate!")

    if args.verbose:
        for c in cookies:
            print(f"  {c['name']}: {c['domain']} ({'secure' if c['secure'] else ''})")

    if args.dry_run:
        print("\n---\n\nItems that would be written:")
        print(f"  • {COOKIES_PATH} ({len(cookies)} cookies)")
        print(f"  • {SOURCE_STATE_PATH}")
        print(f"  • {PROFILE_DIR / '.initialized'}")
        print("  • browser-install.json (if patchright browsers found)")
        print("\n--- dry run complete, no files written ---")
        return

    # 3. Write cookies.json
    AUTH_ROOT.mkdir(parents=True, exist_ok=True)
    COOKIES_PATH.write_text(json.dumps(cookies, indent=2))
    print(f"✓ Wrote {COOKIES_PATH} ({len(cookies)} cookies)")

    # 4. Write source-state.json
    source_state = {
        "version": 1,
        "source_runtime_id": "linux-amd64-host",
        "login_generation": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile_path": str(PROFILE_DIR),
        "cookies_path": str(COOKIES_PATH),
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
    }
    SOURCE_STATE_PATH.write_text(json.dumps(source_state, indent=2, sort_keys=True) + "\n")
    print(f"✓ Wrote {SOURCE_STATE_PATH}")

    # 5. Create minimal profile directory
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    (PROFILE_DIR / ".initialized").write_text(f"cookie-injected-session-{uuid.uuid4().hex[:8]}\n")
    print(f"✓ Created profile directory: {PROFILE_DIR}")

    # 6. Write browser-install.json if patchright browsers are found
    patchright_ver = get_patchright_version()
    if patchright_ver:
        installed = browser_installed()
        if installed:
            browser_metadata = {
                "version": 3,
                "runtime_id": "linux-amd64-host",
                "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "browsers_path": str(BROWSERS_DIR),
                "browser_name": "chromium",
                "installer_name": "patchright",
                "patchright_version": patchright_ver,
                "installed_targets": installed,
            }
            BROWSER_INSTALL_PATH.write_text(json.dumps(browser_metadata, indent=2, sort_keys=True) + "\n")
            print(f"✓ Wrote {BROWSER_INSTALL_PATH}")
            if args.verbose:
                print(f"  patchright v{patchright_ver}, targets: {list(installed.keys())}")

    print("\n✅ LinkedIn auth state ready. Restart the MCP server to pick up changes.")
    if not has_li_at:
        print("⚠  WARNING: No li_at cookie found — LinkedIn session won't work.")
        print("   Make sure you're logged into LinkedIn in Firefox on Windows, then re-run.")


if __name__ == "__main__":
    main()
