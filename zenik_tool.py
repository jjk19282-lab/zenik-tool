# ZENIK TOOL v2.8 — FULL CODE (Windows + Mobile/iSH)
# Mobile/iSH mode auto-disables Windows-only tabs (Tools/Gaming).
#
# Optional deps:
#   pip install colorama cryptography pyperclip
#
# Notes:
# - Wi-Fi SSID scan works on Windows (netsh). On iSH/iOS it will likely not work (iOS limitation).
# - Nmap features are SAFE-restricted to private/localhost only (no public scanning).

import os
import time
import platform
import socket
import random
import json
import urllib.request
import base64
import getpass
import math
import subprocess
import re
import ipaddress
import hashlib
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# ------------------ Basic Colors ------------------
RED = ""
BRIGHT = ""
RESET = ""
GREEN = ""
YELLOW = ""
try:
    from colorama import Fore, Style, init as cinit
    cinit(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BRIGHT = Style.BRIGHT
    RESET = Style.RESET_ALL
except Exception:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BRIGHT = "\033[1m"
    RESET = "\033[0m"

# ------------------ Clipboard (optional) ------------------
try:
    import pyperclip
    CLIPBOARD_OK = True
except Exception:
    CLIPBOARD_OK = False
    pyperclip = None

# ------------------ Crypto (Vault) ------------------
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except Exception:
    Fernet = None

APP_NAME = "ZENIK TOOL"
VERSION = "v2.8"

CONFIG_FILE = "config.json"
LOG_FILE = "zenik_tool.log"
NOTES_FILE = "notes.txt"

VAULT_FILE = "zenik_vault.bin"
VAULT_SALT_FILE = "zenik_vault.salt"

# ------------------ Mode Detection ------------------
def is_windows() -> bool:
    return os.name == "nt"

def is_mobile_mode() -> bool:
    # Anything non-Windows we treat as mobile-friendly mode (includes iSH)
    return not is_windows()

def mode_label() -> str:
    return "WINDOWS" if is_windows() else "MOBILE/iSH"

# ------------------ Config + Logging ------------------
DEFAULT_CONFIG = {
    "webhook_url": "",
    "webhook_autosend": True,
    "vault_autolock_minutes": 3,
    "vault_clipboard_clear_seconds": 20,
    "vault_backup_on_exit": True,
    "password_default_length": 16,
    "password_include_symbols": True,
    "saved_targets": [],  # safe Nmap targets (private/localhost only)

    # STYLE TAB
    "theme_name": "RED",
    "logo_name": "ZENIK+DUCK",
    "ascii_style": "CLASSIC",
}

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(cfg if isinstance(cfg, dict) else {})
            if not isinstance(merged.get("saved_targets"), list):
                merged["saved_targets"] = []
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

CONFIG = load_config()

def log_event(msg: str):
    line = f"[{now_str()}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ------------------ STYLE SYSTEM (Theme / Logo / ASCII style) ------------------
THEMES = {
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
}

ASCII_STYLES = {
    "CLASSIC": {"line": "-", "corner": "+", "fill": "."},
    "DOTS":    {"line": ".", "corner": ".", "fill": "."},
    "BLOCKS":  {"line": "█", "corner": "█", "fill": "░"},
    "DOUBLE":  {"line": "═", "corner": "╬", "fill": "·"},
}

LOGOS = {
    "ZENIK+DUCK": r"""
███████╗ ███████╗███╗   ██╗██╗██╗  ██╗
╚══███╔╝ ██╔════╝████╗  ██║██║██║ ██╔╝
  ███╔╝  █████╗  ██╔██╗ ██║██║█████╔╝
 ███╔╝   ██╔══╝  ██║╚██╗██║██║██╔═██╗
███████╗ ███████╗██║ ╚████║██║██║  ██╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝

        _______
       /\ o o o\
      /o \ o o o\_______
     <    >------>   o /|
      \ o/  o   /_____/o|
       \/______/     |oo|
             |   o   |o/
             |_______|/
""",
    "ZENIK_TEXT_ONLY": r"""
███████╗ ███████╗███╗   ██╗██╗██╗  ██╗
╚══███╔╝ ██╔════╝████╗  ██║██║██║ ██╔╝
  ███╔╝  █████╗  ██╔██╗ ██║██║█████╔╝
 ███╔╝   ██╔══╝  ██║╚██╗██║██║██╔═██╗
███████╗ ███████╗██║ ╚████║██║██║  ██╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝
""",
    "DUCK_ONLY": r"""
        _______
       /\ o o o\
      /o \ o o o\_______
     <    >------>   o /|
      \ o/  o   /_____/o|
       \/______/     |oo|
             |   o   |o/
             |_______|/
""",
}

def get_accent() -> str:
    name = str(CONFIG.get("theme_name", "RED") or "RED").upper()
    return THEMES.get(name, "\033[31m")

def get_ascii_style() -> dict:
    name = str(CONFIG.get("ascii_style", "CLASSIC") or "CLASSIC").upper()
    return ASCII_STYLES.get(name, ASCII_STYLES["CLASSIC"])

def get_logo_text() -> str:
    name = str(CONFIG.get("logo_name", "ZENIK+DUCK") or "ZENIK+DUCK")
    return LOGOS.get(name, LOGOS["ZENIK+DUCK"])

# ------------------ ASCII Art (Tab art) ------------------
TAB_ART = {
    "MAIN": r"""
 .:: ZENIK TOOL ::.
....................
""",
    "IPNET": r"""
   . . .  IP / NET
  .:.:.:.
   ' ' '
""",
    "UTILS": r"""
  [*] UTILITIES
  ............
""",
    "TOOLS": r"""
  [#] TOOLS (WIN)
  ............
""",
    "GAMING": r"""
  [>] GAMING (WIN)
  ............
""",
    "STYLE": r"""
  [~] STYLE
  ............
""",
    "NETWORK": r"""
  .-..-.  net
 ( WiFi ).....
  `-''-'
""",
    "IP": r"""
   . . .  ip
  .:.:.:.
   ' ' '
""",
    "MAP": r"""
  .----.
 / .--. \  map
 | |  | |
 \ '--' /
  '----'
""",
    "DIST": r"""
  . . . .  dist
   \  |  /
    \ | /
     \/
""",
    "PING": r"""
  .....
 . ping .
  .....
""",
    "PASS": r"""
  [*****] pass
  [*****]
""",
    "NOTES": r"""
  .----.
  |note|
  '----'
""",
    "VAULT": r"""
  .------.
  |VAULT |
  '------'
""",
    "WEBHOOK": r"""
  <hook> webhook
  .......
""",
    "SETTINGS": r"""
  [=] settings
  [=]
""",
    "LOGS": r"""
  .----.
  |log |
  '----'
""",
    "HASH": r"""
  [sha256]
  [md5...]
""",
}

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def pause():
    try:
        input("\nPress ENTER to continue...")
    except KeyboardInterrupt:
        pass

def header(title: str = "", tab_key: str = "MAIN"):
    clear()
    ACCENT = get_accent()
    style = get_ascii_style()
    line = style["line"]

    print(ACCENT + get_logo_text() + RESET)
    print(BRIGHT + ACCENT + f"              {APP_NAME} {VERSION}" + RESET)
    print(ACCENT + f"              MODE: {mode_label()}" + RESET)  # <-- (4) Mode label added
    if title:
        print(ACCENT + f"              {title}" + RESET)
    print(ACCENT + (line * 60) + RESET)
    print(ACCENT + TAB_ART.get(tab_key, TAB_ART["MAIN"]) + RESET)

# ------------------ Helpers ------------------
def run_cmd(cmd: List[str], timeout: int = 12) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return 1, "", str(e)

def which(tool: str) -> Optional[str]:
    return shutil.which(tool)

def find_windows_exe(candidates: List[str]) -> Optional[str]:
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

def open_url(url: str):
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception:
        print("Could not open browser. URL:", url)

def resolve_to_ip(target: str):
    target = target.strip()
    if not target:
        return None
    try:
        return ipaddress.ip_address(target)
    except Exception:
        pass
    try:
        ip_str = socket.gethostbyname(target)
        return ipaddress.ip_address(ip_str)
    except Exception:
        return None

def is_private_or_local(ip_obj) -> bool:
    try:
        return bool(ip_obj.is_private or ip_obj.is_loopback)
    except Exception:
        return False

def safe_target_guard(target: str) -> Tuple[bool, str]:
    ip_obj = resolve_to_ip(target)
    if ip_obj is None:
        return False, "Could not resolve target to an IP."
    if not is_private_or_local(ip_obj):
        return False, f"Blocked: target resolves to {ip_obj} (public IP). Only private/localhost allowed."
    return True, str(ip_obj)

def safe_network_guard(cidr: str) -> Tuple[bool, str]:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        if not (net.is_private or net.is_loopback):
            return False, "Blocked: only private/localhost networks allowed."
        return True, str(net)
    except Exception:
        return False, "Invalid CIDR/network."

def is_admin_windows() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

# ------------------ Clipboard helpers ------------------
def clip_copy(text: str):
    if not CLIPBOARD_OK:
        print("\nClipboard not available. Install: pip install pyperclip")
        return
    try:
        pyperclip.copy(text)
        print("\nCopied to clipboard.")
    except Exception as e:
        print("\nClipboard copy failed:", e)

def clip_copy_autoclear(text: str, seconds: int):
    if not CLIPBOARD_OK:
        print("\nClipboard not available. Install: pip install pyperclip")
        return
    try:
        pyperclip.copy(text)
        print(f"\nCopied to clipboard. Auto-clear in {seconds}s…")
        if seconds and seconds > 0:
            time.sleep(seconds)
            try:
                cur = pyperclip.paste()
            except Exception:
                cur = None
            if cur == text:
                pyperclip.copy("")
                print("Clipboard cleared ✅")
    except Exception as e:
        print("\nClipboard copy failed:", e)

# ------------------ Webhook (Embeds) ------------------
def get_webhook_url() -> str:
    return str(CONFIG.get("webhook_url", "") or "").strip()

def webhook_send(content: Optional[str] = None, username: str = APP_NAME, embed: Optional[Dict[str, Any]] = None) -> bool:
    url = get_webhook_url()
    if not url:
        return False

    payload: Dict[str, Any] = {"username": username}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ZENIK-TOOL"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False

def make_ip_embed(data: Dict[str, Any], scanned_from: str) -> Dict[str, Any]:
    return {
        "title": "🌍 IP Lookup Result",
        "description": f"**IP Scanned From:** `{scanned_from}`",
        "color": 16711680,
        "fields": [
            {"name": "IP", "value": str(data.get("query", "N/A")), "inline": True},
            {
                "name": "Location",
                "value": f"{data.get('city','N/A')}, {data.get('regionName','N/A')}, {data.get('country','N/A')}",
                "inline": True,
            },
            {
                "name": "ISP / ASN",
                "value": f"{data.get('isp','N/A')}\n{data.get('as','N/A')}",
                "inline": False,
            },
        ],
        "footer": {"text": f"{APP_NAME} {VERSION} • {now_str()}"},
    }

def webhook_menu():
    while True:
        header("WEBHOOK (SAVED)", "WEBHOOK")
        url_set = "SET" if get_webhook_url() else "NOT SET"
        autosend = "ON" if CONFIG.get("webhook_autosend", True) else "OFF"
        print(f"Webhook: {url_set} | Auto-send on IP lookup: {autosend}")
        print("""
[1] Set/Change Webhook URL (saved)
[2] Toggle Auto-send (IP lookup embeds)
[3] Send EMBED Test
[4] Send Custom TEXT message
[0] Back
""")
        c = input("> ").strip()

        if c == "1":
            header("WEBHOOK - SET URL (SAVED)", "WEBHOOK")
            print("Paste your Discord webhook URL (leave empty to cancel).")
            url = input("URL: ").strip()
            if url:
                CONFIG["webhook_url"] = url
                save_config(CONFIG)
                log_event("Webhook URL updated (saved).")
                print("\nSaved ✅")
            else:
                print("\nCancelled.")
            pause()

        elif c == "2":
            CONFIG["webhook_autosend"] = not bool(CONFIG.get("webhook_autosend", True))
            save_config(CONFIG)
            log_event(f"Webhook auto-send toggled to {CONFIG['webhook_autosend']}.")
            print("\nToggled ✅")
            pause()

        elif c == "3":
            header("WEBHOOK - EMBED TEST", "WEBHOOK")
            embed = {
                "title": "✅ ZENIK TOOL Webhook Test",
                "description": "Embed test message from your tool.",
                "color": 16711680,
                "fields": [
                    {"name": "Version", "value": VERSION, "inline": True},
                    {"name": "Mode", "value": mode_label(), "inline": True},
                    {"name": "Time", "value": now_str(), "inline": False},
                ],
                "footer": {"text": "ZENIK TOOL"},
            }
            ok = webhook_send(embed=embed)
            log_event("Webhook embed test " + ("sent." if ok else "failed."))
            print("Sent!" if ok else "Failed (URL missing/invalid or no internet).")
            pause()

        elif c == "4":
            header("WEBHOOK - CUSTOM TEXT", "WEBHOOK")
            msg = input("Message: ").rstrip()
            if not msg:
                print("Cancelled.")
                pause()
                continue
            ok = webhook_send(content=msg)
            log_event("Webhook custom text " + ("sent." if ok else "failed."))
            print("Sent!" if ok else "Failed.")
            pause()

        elif c == "0":
            return

        else:
            print("Invalid.")
            time.sleep(0.6)

# ------------------ IP / GEO / DISTANCE ------------------
def fetch_ip_data(ip: Optional[str]):
    fields = ",".join([
        "status","message","query",
        "continent","continentCode",
        "country","countryCode",
        "region","regionName",
        "city","district","zip",
        "lat","lon",
        "timezone","offset",
        "currency",
        "isp","org","as","asname",
        "reverse",
        "mobile","proxy","hosting"
    ])
    url = f"http://ip-api.com/json/{ip}?fields={fields}" if ip else f"http://ip-api.com/json/?fields={fields}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as response:
        data = json.loads(response.read().decode("utf-8", errors="ignore"))
    return data

def ip_lookup() -> Optional[Dict[str, Any]]:
    header("IP LOOKUP (EXTRA INFO)", "IP")
    ip_in = input("Enter IP (leave empty for your IP): ").strip()
    ip = ip_in if ip_in else None

    try:
        data = fetch_ip_data(ip)
        if data.get("status") != "success":
            print("Lookup failed.")
            print("Status:", data.get("status"))
            if data.get("message"):
                print("Message:", data.get("message"))
            log_event(f"IP lookup failed ({'user ip' if ip is None else ip_in}).")
            pause()
            return None

        header("IP LOOKUP RESULTS", "IP")
        ipq = data.get("query","N/A")
        scanned_from = "User's IP" if ip is None else "Provided IP"

        print(f"IP: {ipq}")
        print(f"Scanned From: {scanned_from}")
        print(f"Reverse DNS / Hostname: {data.get('reverse','N/A')}")

        print("\nLocation")
        print(f"Country:   {data.get('country','N/A')} ({data.get('countryCode','N/A')})")
        print(f"Region:    {data.get('regionName','N/A')}")
        print(f"City:      {data.get('city','N/A')}")
        print(f"ZIP:       {data.get('zip','N/A')}")

        lat = data.get("lat", None)
        lon = data.get("lon", None)
        if lat is not None and lon is not None:
            maps = f"https://www.google.com/maps?q={lat},{lon}"
            print(f"Lat/Lon:   {lat}, {lon}")
            print(f"Maps:      {maps}")

        print("\nNetwork")
        print(f"ISP:       {data.get('isp','N/A')}")
        print(f"ASN:       {data.get('as','N/A')}")
        print(f"ASN Name:  {data.get('asname','N/A')}")

        print("\nFlags (reputation-ish)")
        print(f"Mobile:    {data.get('mobile','N/A')}")
        print(f"Proxy:     {data.get('proxy','N/A')}")
        print(f"Hosting:   {data.get('hosting','N/A')}")

        if get_webhook_url() and bool(CONFIG.get("webhook_autosend", True)):
            embed = make_ip_embed(data, scanned_from)
            webhook_send(embed=embed)

        log_event(f"IP lookup done ({scanned_from}): {ipq} ({data.get('country','?')}, {data.get('city','?')})")
        pause()
        return data

    except Exception as e:
        print("Lookup error:", e)
        log_event(f"IP lookup error: {e}")
        pause()
        return None

def render_geo_map(lat: float, lon: float, label: str = "X") -> str:
    world = [
        "  . _.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.. .  ",
        "  :     .        _..---.._         _..---.._          _..---.._       :  ",
        "  :   .   _..-''           ''-.._.'           ''-.._.'          ''-.. :  ",
        "  :  _.-'     _..-''-.._         _..-''-.._         _..-''-.._        :  ",
        "  :-'       .'  _.._   '.      .'  _.._   '.      .'  _.._   '.       :  ",
        "  :        /  .'    '.   \\    /  .'    '.   \\    /  .'    '.   \\      :  ",
        "  :       ;  /  _  _  \\   ;  ;  /  _  _  \\   ;  ;  /  _  _  \\   ;     :  ",
        "  :       |  | ( )( ) |   |  |  | ( )( ) |   |  |  | ( )( ) |   |     :  ",
        "  :       ;  \\  __    /   ;  ;  \\  __    /   ;  ;  \\  __    /   ;     :  ",
        "  :        \\  '.____.'   /    \\  '.____.'   /    \\  '.____.'   /      :  ",
        "  :         '.         .'      '.         .'      '.         .'       :  ",
        "  :            ''-..-''            ''-..-''            ''-..-''        :  ",
        "  :                                                                         :",
        "  ' .._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.._.. '  ",
    ]
    h = len(world)
    w = len(world[0])
    row = int((90 - lat) / 180 * (h - 1))
    col = int((lon + 180) / 360 * (w - 1))
    row = max(0, min(h - 1, row))
    col = max(0, min(w - 1, col))
    line = list(world[row])
    line[col] = label
    world[row] = "".join(line)
    return "\n".join(world)

def geo_map():
    header("GEO MAP", "MAP")
    ip_in = input("Enter IP for map (leave empty for your IP): ").strip()
    ip = ip_in if ip_in else None
    try:
        data = fetch_ip_data(ip)
        if data.get("status") != "success":
            print("Invalid IP or lookup failed.")
            log_event("Geo map failed (lookup).")
            pause()
            return
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))

        header("GEO MAP RESULT", "MAP")
        print(f"IP: {data.get('query')}  |  {data.get('city')}, {data.get('regionName')}, {data.get('country')}")
        print(f"Lat/Lon: {lat}, {lon}\n")

        map_txt = render_geo_map(lat, lon, "X").replace("X", f"{get_accent()}X{RESET}", 1)
        print(map_txt)

        log_event(f"Geo map viewed: {data.get('query')} ({lat},{lon})")
        pause()
    except Exception as e:
        print("Geo map failed:", e)
        log_event(f"Geo map error: {e}")
        pause()

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def distance_tool():
    header("DISTANCE (Your IP ↔ Another IP)", "DIST")
    print("This compares your public IP location to another IP location.\n")
    try:
        me = fetch_ip_data(None)
        if me.get("status") != "success":
            print("Could not get your IP location.")
            pause()
            return

        ip2_in = input("Enter other IP: ").strip()
        if not ip2_in:
            print("Cancelled.")
            pause()
            return

        other = fetch_ip_data(ip2_in)
        if other.get("status") != "success":
            print("Invalid IP / lookup failed.")
            pause()
            return

        lat1, lon1 = float(me["lat"]), float(me["lon"])
        lat2, lon2 = float(other["lat"]), float(other["lon"])
        km = haversine_km(lat1, lon1, lat2, lon2)
        mi = km * 0.621371

        header("DISTANCE RESULT", "DIST")
        print(f"Your IP:  {me.get('query')}  |  {me.get('city')}, {me.get('regionName')}, {me.get('country')}")
        print(f"Other IP: {other.get('query')}  |  {other.get('city')}, {other.get('regionName')}, {other.get('country')}")
        print(f"\nDistance: ~{km:,.1f} km  (~{mi:,.1f} miles)")

        log_event(f"Distance calc: me({me.get('query')}) to {other.get('query')} = {km:.1f} km")
        pause()
    except Exception as e:
        print("Distance tool failed:", e)
        log_event(f"Distance tool error: {e}")
        pause()

def local_ip():
    header("LOCAL IP", "NETWORK")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        print("Local IP:", s.getsockname()[0])
        s.close()
        log_event("Viewed local IP.")
    except Exception as e:
        print("Failed:", e)
        log_event(f"Local IP error: {e}")
    pause()

# ------------------ Wi-Fi / Network (Nearby SSIDs ONLY) ------------------
def list_nearby_ssids() -> List[str]:
    ssids: List[str] = []
    if os.name == "nt":
        code, out, _ = run_cmd(["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=20)
        if code == 0 and out:
            for line in out.splitlines():
                m = re.match(r"\s*SSID\s+\d+\s*:\s*(.*)\s*$", line)
                if m:
                    name = m.group(1).strip()
                    if name and name.lower() != "<hidden network>":
                        ssids.append(name)
    else:
        # iOS/iSH generally cannot scan nearby SSIDs due to platform limits.
        ssids = []
    uniq, seen = [], set()
    for s in ssids:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq

def network_overview():
    header("NETWORK OVERVIEW", "NETWORK")
    print("OS:", platform.system(), platform.release())
    print("Hostname:", socket.gethostname())

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lip = s.getsockname()[0]
        s.close()
        print("Local IP:", lip)
    except Exception:
        print("Local IP: (unknown)")

    try:
        with urllib.request.urlopen(
            urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "Mozilla/5.0"}),
            timeout=6
        ) as r:
            pub = r.read().decode("utf-8", errors="ignore").strip()
        print("Public IP:", pub)
    except Exception:
        print("Public IP: (failed)")

    print("\nNearby Wi-Fi networks (SSID only):")
    ssids = list_nearby_ssids()
    if not ssids:
        if is_mobile_mode():
            print("- Not available on iOS/iSH (platform limitation).")
        else:
            print("- (none found or Wi-Fi off / permission)")
    else:
        for i, s in enumerate(ssids[:30], start=1):
            print(f"- {i:02d}. {s}")

    log_event(f"Network overview opened. SSIDs_found={len(ssids)}")
    pause()

def wifi_scan_only():
    header("WIFI SCAN (SSID ONLY)", "NETWORK")
    print("Shows nearby Wi-Fi network names (SSID).")
    print("No passwords, no hacking, no joining.\n")

    ssids = list_nearby_ssids()
    if not ssids:
        if is_mobile_mode():
            print("Not supported on iOS/iSH (platform limitation).")
        else:
            print("No SSIDs found. (Wi-Fi off, driver issue, or permission)")
        log_event("WiFi scan: none found / unsupported.")
        pause()
        return

    print(f"Found {len(ssids)} SSIDs:\n")
    for i, s in enumerate(ssids[:60], start=1):
        print(f"{i:02d}) {s}")

    log_event(f"WiFi scan: SSIDs_found={len(ssids)}")
    pause()

# ------------------ Utilities ------------------
def system_info():
    header("SYSTEM INFO", "UTILS")
    print("OS:", platform.system(), platform.release())
    print("Machine:", platform.machine())
    print("Processor:", platform.processor() or "Unknown")
    print("Python:", platform.python_version())
    print("User:", os.getenv("USERNAME") or os.getenv("USER") or "Unknown")
    log_event("Viewed system info.")
    pause()

def ping_tool():
    header("PING", "PING")
    host = input("Host to ping (example: google.com): ").strip()
    if not host:
        return
    count = input("How many pings? (default 4): ").strip() or "4"
    cmd = f"ping -n {count} {host}" if os.name == "nt" else f"ping -c {count} {host}"
    print("\n" + cmd + "\n")
    os.system(cmd)
    log_event(f"Ping executed: host={host} count={count}")
    pause()

def password_entropy_bits(pw: str) -> float:
    if not pw:
        return 0.0
    pool = 0
    if any("a" <= c <= "z" for c in pw): pool += 26
    if any("A" <= c <= "Z" for c in pw): pool += 26
    if any(c.isdigit() for c in pw):     pool += 10
    if any(not c.isalnum() for c in pw): pool += 32
    pool = max(pool, 1)
    return len(pw) * math.log2(pool)

def password_strength_label(bits: float) -> str:
    if bits < 40: return "WEAK 🔴"
    if bits < 60: return "OK 🟠"
    if bits < 80: return "STRONG 🟢"
    return "VERY STRONG 🟢🟢"

def password_generator():
    header("PASSWORD GENERATOR + STRENGTH", "PASS")
    default_len = int(CONFIG.get("password_default_length", 16) or 16)
    default_symbols = bool(CONFIG.get("password_include_symbols", True))

    length_str = input(f"Length (default {default_len}): ").strip()
    length = int(length_str) if length_str.isdigit() else default_len
    length = max(8, min(64, length))

    sym_in = input(f"Include symbols? (y/n default {'y' if default_symbols else 'n'}): ").strip().lower()
    if sym_in in ("y", "yes"):
        include_symbols = True
    elif sym_in in ("n", "no"):
        include_symbols = False
    else:
        include_symbols = default_symbols

    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    if include_symbols:
        chars += "!@#$%^&*-_+="

    pwd = "".join(random.choice(chars) for _ in range(length))
    bits = password_entropy_bits(pwd)

    print("\nGenerated Password:\n")
    print(BRIGHT + pwd + RESET)
    print(f"\nStrength: {password_strength_label(bits)}")
    print(f"Entropy:  {bits:.1f} bits")

    log_event(f"Password generated (len={length}, symbols={include_symbols}, strength={password_strength_label(bits)})")
    pause()

def notes():
    header("NOTES", "NOTES")
    note = input("Write note: ")
    if note:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now_str()}] {note}\n")
        print("Saved.")
        log_event("Saved note.")
    pause()

def view_logs():
    header("ACTIVITY LOGS", "LOGS")
    if not os.path.exists(LOG_FILE):
        print("No logs yet.")
        pause()
        return
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-250:]
        print("".join(lines) if lines else "No logs yet.")
    except Exception as e:
        print("Could not read logs:", e)
    pause()

# ------------------ Vault (Encrypted) ------------------
def vault_available():
    return Fernet is not None

def vault_autolock_minutes() -> int:
    try:
        return max(1, int(CONFIG.get("vault_autolock_minutes", 3)))
    except Exception:
        return 3

def vault_get_or_create_salt(path: str):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    salt = os.urandom(16)
    with open(path, "wb") as f:
        f.write(salt)
    return salt

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

def vault_load(fernet: "Fernet", vault_path: str) -> dict:
    if not os.path.exists(vault_path):
        return {"items": []}
    with open(vault_path, "rb") as f:
        token = f.read()
    raw = fernet.decrypt(token)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        return {"items": []}
    return data

def vault_save(fernet: "Fernet", data: dict, vault_path: str):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    token = fernet.encrypt(raw)
    with open(vault_path, "wb") as f:
        f.write(token)

def mask_secret(s: str, keep: int = 2) -> str:
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "*" * (len(s) - keep)

def parse_tags(s: str) -> List[str]:
    raw = s.replace(",", " ").split()
    tags = []
    for t in raw:
        t = t.strip().lower()
        if t and t not in tags:
            tags.append(t)
    return tags

def format_tags(tags: Any) -> str:
    if isinstance(tags, list) and tags:
        return ", ".join(tags)
    return ""

def vault_unlock(vault_path: str = VAULT_FILE, salt_path: str = VAULT_SALT_FILE):
    if not vault_available():
        header("VAULT", "VAULT")
        print("Vault requires: pip install cryptography")
        pause()
        return None

    header("VAULT - UNLOCK", "VAULT")
    salt = vault_get_or_create_salt(salt_path)
    pw = getpass.getpass("Master password: ")
    if not pw:
        return None

    key = derive_key_from_password(pw, salt)
    f = Fernet(key)

    try:
        _ = vault_load(f, vault_path)
        return f
    except InvalidToken:
        print("\nWrong master password (or vault corrupted).")
        pause()
        return None
    except Exception as e:
        print("\nVault error:", e)
        pause()
        return None

def vault_autolock_check(last_activity_ts: float) -> bool:
    return (time.time() - last_activity_ts) >= (vault_autolock_minutes() * 60)

def vault_view_items(items: list, tag_filter: Optional[str] = None):
    shown = 0
    for i, it in enumerate(items, start=1):
        tags = it.get("tags", [])
        if tag_filter and tag_filter not in (tags or []):
            continue
        itype = it.get("type", "note")
        print(f"\n#{i}  [{itype.upper()}]  {it.get('title','(no title)')}")
        print("Added:", it.get("created_at", ""))
        if it.get("updated_at"):
            print("Updated:", it.get("updated_at", ""))
        tline = format_tags(tags)
        if tline:
            print("Tags:", tline)
        if itype == "login":
            print("Username:", it.get("username", ""))
            print("Password:", mask_secret(it.get("password", "")))
            print("URL:     ", it.get("url", ""))
            note = it.get("note", "")
            if note:
                print("Note:    ", note)
        else:
            print("Value:", it.get("value", ""))
        shown += 1
    if shown == 0:
        print("No matching items.")

def vault_pick_item(items: list) -> Optional[int]:
    if not items:
        return None
    for i, it in enumerate(items, start=1):
        t = it.get("title", "(no title)")
        ty = it.get("type", "note")
        tg = format_tags(it.get("tags", []))
        extra = f" | tags: {tg}" if tg else ""
        print(f"[{i}] {t} ({ty}){extra}")
    s = input("Pick number: ").strip()
    if not s.isdigit():
        return None
    n = int(s)
    if 1 <= n <= len(items):
        return n - 1
    return None

def vault_add_note(data: dict) -> bool:
    header("VAULT - ADD NOTE", "VAULT")
    title = input("Title: ").strip()
    value = input("Note text: ").rstrip()
    tags = parse_tags(input("Tags (comma/space, optional): ").strip())
    if not title or not value:
        print("Cancelled (title & text required).")
        pause()
        return False
    data["items"].append({
        "type": "note",
        "title": title,
        "value": value,
        "tags": tags,
        "created_at": now_str(),
    })
    return True

def vault_add_login(data: dict) -> bool:
    header("VAULT - ADD LOGIN", "VAULT")
    title = input("Title (example: Roblox / Gmail): ").strip()
    username = input("Username/email: ").strip()
    password = getpass.getpass("Password (hidden): ").strip()
    url = input("URL (optional): ").strip()
    note = input("Note (optional): ").strip()
    tags = parse_tags(input("Tags (comma/space, optional): ").strip())
    if not title or not username or not password:
        print("Cancelled (title, username, password required).")
        pause()
        return False
    data["items"].append({
        "type": "login",
        "title": title,
        "username": username,
        "password": password,
        "url": url,
        "note": note,
        "tags": tags,
        "created_at": now_str(),
    })
    return True

def vault_search(items: list) -> List[dict]:
    header("VAULT - SEARCH", "VAULT")
    q = input("Search text: ").strip().lower()
    if not q:
        return []
    hits = []
    for it in items:
        blob = json.dumps(it, ensure_ascii=False).lower()
        if q in blob:
            hits.append(it)
    return hits

def vault_copy_menu(items: list):
    header("VAULT - COPY / REVEAL", "VAULT")
    if not items:
        print("No items.")
        pause()
        return

    idx = vault_pick_item(items)
    if idx is None:
        print("Cancelled.")
        pause()
        return

    it = items[idx]
    itype = it.get("type", "note")
    clear_s = int(CONFIG.get("vault_clipboard_clear_seconds", 20) or 20)

    if itype == "login":
        print("\nWhat do you want?")
        print("[1] Copy Username")
        print("[2] Copy Password (auto-clear)")
        print("[3] Reveal Password (shows on screen)")
        print("[4] Copy URL")
        print("[5] Copy Note")
        print("[0] Back")
        c = input("> ").strip()

        if c == "1":
            clip_copy(it.get("username", ""))
            pause()
        elif c == "2":
            clip_copy_autoclear(it.get("password", ""), clear_s)
            log_event(f"Vault: password copied (auto-clear {clear_s}s).")
            pause()
        elif c == "3":
            header("VAULT - REVEAL PASSWORD", "VAULT")
            print("Password:\n")
            print(BRIGHT + it.get("password", "") + RESET)
            log_event("Vault: password revealed on screen.")
            pause()
        elif c == "4":
            clip_copy(it.get("url", ""))
            pause()
        elif c == "5":
            clip_copy(it.get("note", ""))
            pause()
        else:
            return
    else:
        clip_copy(it.get("value", ""))
        pause()

def vault_menu():
    f = vault_unlock()
    if not f:
        return
    last_activity = time.time()
    while True:
        if vault_autolock_check(last_activity):
            header("VAULT", "VAULT")
            print(f"Auto-locked after {vault_autolock_minutes()} min inactivity.")
            log_event("Vault auto-locked.")
            pause()
            return

        data = vault_load(f, VAULT_FILE)
        items = data.get("items", [])

        header("VAULT (ENCRYPTED)", "VAULT")
        print(f"Auto-lock: {vault_autolock_minutes()} min | Clipboard: {'OK' if CLIPBOARD_OK else 'NO'} | Auto-clear: {CONFIG.get('vault_clipboard_clear_seconds', 20)}s")
        print("""
[1] View items
[2] View by tag
[3] Add NOTE (with tags)
[4] Add LOGIN (with tags)
[5] Delete item
[6] Search
[7] Copy / Reveal (clipboard auto-clear)
[8] Lock now
[0] Back
""")
        choice = input("> ").strip()
        last_activity = time.time()

        if choice == "1":
            header("VAULT - VIEW", "VAULT")
            vault_view_items(items)
            pause()
        elif choice == "2":
            header("VAULT - VIEW BY TAG", "VAULT")
            tag = input("Tag: ").strip().lower()
            if tag:
                vault_view_items(items, tag_filter=tag)
            else:
                print("Cancelled.")
            pause()
        elif choice == "3":
            if vault_add_note(data):
                vault_save(f, data, VAULT_FILE)
                log_event("Vault: added NOTE.")
            pause()
        elif choice == "4":
            if vault_add_login(data):
                vault_save(f, data, VAULT_FILE)
                log_event("Vault: added LOGIN.")
            pause()
        elif choice == "5":
            header("VAULT - DELETE", "VAULT")
            if not items:
                print("No items to delete.")
                pause()
                continue
            idx = vault_pick_item(items)
            if idx is None:
                print("Cancelled.")
            else:
                removed = data["items"].pop(idx)
                vault_save(f, data, VAULT_FILE)
                print("Deleted:", removed.get("title", ""))
                log_event(f"Vault: deleted '{removed.get('title','(item)')}'.")
            pause()
        elif choice == "6":
            hits = vault_search(items)
            header("VAULT - SEARCH RESULTS", "VAULT")
            print(f"Results: {len(hits)}")
            vault_view_items(hits)
            pause()
        elif choice == "7":
            vault_copy_menu(items)
        elif choice == "8":
            header("VAULT", "VAULT")
            print("Locked ✅")
            log_event("Vault locked manually.")
            pause()
            return
        elif choice == "0":
            log_event("Vault back.")
            return
        else:
            print("Invalid.")
            time.sleep(0.6)

# ------------------ Settings ------------------
def settings_menu():
    while True:
        header("SETTINGS (SAVED)", "SETTINGS")
        print(f"Vault autolock minutes: {CONFIG.get('vault_autolock_minutes', DEFAULT_CONFIG['vault_autolock_minutes'])}")
        print(f"Vault clipboard clear seconds: {CONFIG.get('vault_clipboard_clear_seconds', DEFAULT_CONFIG['vault_clipboard_clear_seconds'])}")
        print(f"Password default length: {CONFIG.get('password_default_length', DEFAULT_CONFIG['password_default_length'])}")
        print(f"Password include symbols: {CONFIG.get('password_include_symbols', DEFAULT_CONFIG['password_include_symbols'])}")
        print("""
[1] Set Vault Auto-lock Minutes
[2] Set Vault Clipboard Auto-clear Seconds
[3] Set Password Default Length
[4] Toggle Password Symbols Default
[0] Back
""")
        c = input("> ").strip()
        if c == "1":
            header("SET VAULT AUTO-LOCK", "SETTINGS")
            v = input("Minutes (min 1): ").strip()
            if v.isdigit():
                CONFIG["vault_autolock_minutes"] = max(1, int(v))
                save_config(CONFIG)
                log_event(f"Settings: vault_autolock_minutes set to {CONFIG['vault_autolock_minutes']}.")
                print("Saved ✅")
            else:
                print("Cancelled / invalid.")
            pause()
        elif c == "2":
            header("SET CLIPBOARD AUTO-CLEAR", "SETTINGS")
            v = input("Seconds (0 to disable): ").strip()
            if v.isdigit():
                CONFIG["vault_clipboard_clear_seconds"] = max(0, int(v))
                save_config(CONFIG)
                log_event(f"Settings: vault_clipboard_clear_seconds set to {CONFIG['vault_clipboard_clear_seconds']}.")
                print("Saved ✅")
            else:
                print("Cancelled / invalid.")
            pause()
        elif c == "3":
            header("SET PASSWORD DEFAULT LENGTH", "SETTINGS")
            v = input("Length (8-64): ").strip()
            if v.isdigit():
                n = max(8, min(64, int(v)))
                CONFIG["password_default_length"] = n
                save_config(CONFIG)
                log_event(f"Settings: password_default_length set to {n}.")
                print("Saved ✅")
            else:
                print("Cancelled / invalid.")
            pause()
        elif c == "4":
            CONFIG["password_include_symbols"] = not bool(CONFIG.get("password_include_symbols", True))
            save_config(CONFIG)
            log_event(f"Settings: password_include_symbols set to {CONFIG['password_include_symbols']}.")
            print("Toggled ✅")
            pause()
        elif c == "0":
            return
        else:
            print("Invalid.")
            time.sleep(0.6)

# ------------------ File Hash Tool ------------------
def file_hash_tool():
    header("FILE HASH (SHA256/MD5)", "HASH")
    path = input("File path: ").strip().strip('"')
    if not path:
        return
    if not os.path.exists(path) or not os.path.isfile(path):
        print("File not found.")
        pause()
        return

    algo = input("Algorithm (1=SHA256 default, 2=MD5): ").strip()
    use_md5 = (algo == "2")

    h = hashlib.md5() if use_md5 else hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        print("\nHash:", h.hexdigest())
        log_event(f"File hash computed: {'MD5' if use_md5 else 'SHA256'} {path}")
    except Exception as e:
        print("Hashing failed:", e)
        log_event(f"File hash failed: {e}")
    pause()

# ------------------ Windows Tools Tab (only used on Windows) ------------------
def nmap_path_windows() -> Optional[str]:
    p = which("nmap")
    if p:
        return p
    candidates = [
        r"C:\Program Files (x86)\Nmap\nmap.exe",
        r"C:\Program Files\Nmap\nmap.exe",
    ]
    return find_windows_exe(candidates)

def wireshark_path_windows() -> Optional[str]:
    p = which("wireshark")
    if p:
        return p
    candidates = [
        r"C:\Program Files\Wireshark\Wireshark.exe",
        r"C:\Program Files (x86)\Wireshark\Wireshark.exe",
    ]
    return find_windows_exe(candidates)

def nmap_info_windows():
    header("NMAP — WINDOWS CHECK", "TOOLS")
    p = nmap_path_windows()
    if not p:
        print("Nmap not found.")
        print("\n[1] Open Nmap download page")
        print("[0] Back")
        c = input("> ").strip()
        if c == "1":
            open_url("https://nmap.org/download.html")
            log_event("Opened Nmap download page.")
        pause()
        return
    code, out, err = run_cmd([p, "--version"], timeout=10)
    print(out.strip() if out.strip() else err.strip())
    log_event("Nmap version checked (Windows).")
    pause()

def nmap_safe_ping_scan_windows(target: str):
    p = nmap_path_windows()
    if not p:
        print("Nmap not installed.")
        pause()
        return

    if "/" in target:
        ok, msg = safe_network_guard(target)
        if not ok:
            print(msg)
            log_event(f"Nmap blocked (public/invalid network): {target}")
            pause()
            return
        safe_target = target
    else:
        ok, msg = safe_target_guard(target)
        if not ok:
            print(msg)
            log_event(f"Nmap blocked target: {target} -> {msg}")
            pause()
            return
        safe_target = target

    header("NMAP — RUNNING (SAFE PING SCAN)", "TOOLS")
    print("Running:", f'"{p}" -sn {safe_target}')
    print("\n(Host discovery only.)\n")
    code, out, err = run_cmd([p, "-sn", safe_target], timeout=45)
    print(out if out else err)
    log_event(f"Nmap safe ping scan ran (Windows): {safe_target}")
    pause()

def nmap_safe_port_scan_windows(target: str, ports: str):
    p = nmap_path_windows()
    if not p:
        print("Nmap not installed.")
        pause()
        return

    ok, msg = safe_target_guard(target)
    if not ok:
        print(msg)
        log_event(f"Nmap blocked target: {target} -> {msg}")
        pause()
        return

    if re.fullmatch(r"\d{1,4}-\d{1,4}", ports):
        a, b = ports.split("-")
        if int(a) < 1 or int(b) > 1024 or int(a) > int(b):
            print("Blocked: port ranges must be within 1-1024.")
            pause()
            return
    else:
        parts = [p.strip() for p in ports.split(",") if p.strip()]
        if not parts or any((not p.isdigit()) or int(p) < 1 or int(p) > 1024 for p in parts):
            print("Blocked: only ports 1-1024 allowed (example: 22,80,443).")
            pause()
            return

    header("NMAP — RUNNING (SAFE PORT SCAN)", "TOOLS")
    print("Running:", f'"{p}" -Pn -sT -p {ports} {target}')
    print("\n(TCP connect scan, ports <=1024, private targets only.)\n")
    code, out, err = run_cmd([p, "-Pn", "-sT", "-p", ports, target], timeout=60)
    print(out if out else err)
    log_event(f"Nmap safe port scan ran (Windows): target={target} ports={ports}")
    pause()

def wireshark_launch_windows():
    header("WIRESHARK — LAUNCH (WINDOWS)", "TOOLS")
    p = wireshark_path_windows()
    if not p:
        print("Wireshark not found.")
        print("\n[1] Open Wireshark download page")
        print("[0] Back")
        c = input("> ").strip()
        if c == "1":
            open_url("https://www.wireshark.org/download.html")
            log_event("Opened Wireshark download page.")
        pause()
        return
    try:
        subprocess.Popen([p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_event("Wireshark launched (Windows).")
        print("Launched ✅")
    except Exception as e:
        print("Failed:", e)
        log_event(f"Wireshark launch failed (Windows): {e}")
    pause()

def nslookup_tool():
    header("NSLOOKUP (DNS)", "TOOLS")
    host = input("Hostname (example: example.com): ").strip()
    if not host:
        return
    code, out, err = run_cmd(["nslookup", host], timeout=20)
    print(out if out else err)
    log_event(f"nslookup ran: {host}")
    pause()

def tracert_tool():
    header("TRACERT", "TOOLS")
    host = input("Host (example: google.com): ").strip()
    if not host:
        return
    code, out, err = run_cmd(["tracert", host], timeout=90)
    print(out if out else err)
    log_event(f"tracert ran: {host}")
    pause()

def ipconfig_all():
    header("IPCONFIG /ALL", "TOOLS")
    code, out, err = run_cmd(["ipconfig", "/all"], timeout=25)
    print(out if out else err)
    log_event("ipconfig /all viewed.")
    pause()

def tools_tab():
    while True:
        header("TAB 3 — TOOLS (WINDOWS)", "TOOLS")
        admin = "ADMIN ✅" if is_admin_windows() else "ADMIN ❌"
        nmap_ok = "YES" if nmap_path_windows() else "NO"
        wire_ok = "YES" if wireshark_path_windows() else "NO"
        print(f"{admin} | Nmap installed: {nmap_ok} | Wireshark installed: {wire_ok}")

        print("""
[1] Nmap: Check installed/version
[2] Nmap: SAFE Ping Scan (private/localhost only)
[3] Nmap: SAFE Port Scan (ports <=1024, private/localhost only)
[4] Wireshark: Launch
[5] tracert (route to host)
[6] nslookup (DNS)
[7] ipconfig /all
[8] File Hash (SHA256/MD5)
[0] Back
""")
        c = input("> ").strip()

        if c == "1":
            nmap_info_windows()
        elif c == "2":
            header("NMAP — SAFE PING SCAN", "TOOLS")
            target = input("Target: ").strip()
            if target:
                nmap_safe_ping_scan_windows(target)
        elif c == "3":
            header("NMAP — SAFE PORT SCAN", "TOOLS")
            target = input("Target: ").strip()
            if target:
                ports = input("Ports (default 1-1024): ").strip() or "1-1024"
                nmap_safe_port_scan_windows(target, ports)
        elif c == "4":
            wireshark_launch_windows()
        elif c == "5":
            tracert_tool()
        elif c == "6":
            nslookup_tool()
        elif c == "7":
            ipconfig_all()
        elif c == "8":
            file_hash_tool()
        elif c == "0":
            return
        else:
            print("Invalid option.")
            time.sleep(0.6)

# ------------------ GAMING TAB (Windows) ------------------
def gaming_tab():
    header("TAB 4 — GAMING (WINDOWS)", "GAMING")
    print("Windows gaming helpers live here. (This tab is Windows-only.)")
    pause()

# ------------------ STYLE TAB ------------------
def style_change_colors_menu():
    while True:
        header("STYLE — CHANGE COLORS", "STYLE")
        current = str(CONFIG.get("theme_name", "RED") or "RED").upper()
        print(f"Current: {current}\n")

        names = list(THEMES.keys())
        for i, n in enumerate(names, start=1):
            print(f"[{i}] {THEMES[n]}{n}{RESET}")
        print("\n[0] Back")

        c = input("> ").strip()
        if c == "0":
            return
        if c.isdigit():
            idx = int(c) - 1
            if 0 <= idx < len(names):
                CONFIG["theme_name"] = names[idx]
                save_config(CONFIG)
                log_event(f"Theme changed to {names[idx]}")
                print("Saved ✅")
                time.sleep(0.6)

def style_change_logo_menu():
    while True:
        header("STYLE — CHANGE LOGO", "STYLE")
        current = str(CONFIG.get("logo_name", "ZENIK+DUCK") or "ZENIK+DUCK")
        print(f"Current: {current}\n")

        names = list(LOGOS.keys())
        for i, n in enumerate(names, start=1):
            print(f"[{i}] {n}")
        print("\n[9] Preview current")
        print("[0] Back")

        c = input("> ").strip()
        if c == "0":
            return
        if c == "9":
            header("STYLE — LOGO PREVIEW", "STYLE")
            print(get_logo_text())
            pause()
            continue
        if c.isdigit():
            idx = int(c) - 1
            if 0 <= idx < len(names):
                CONFIG["logo_name"] = names[idx]
                save_config(CONFIG)
                log_event(f"Logo changed to {names[idx]}")
                print("Saved ✅")
                time.sleep(0.6)

def style_change_ascii_menu():
    while True:
        header("STYLE — ASCII STYLE", "STYLE")
        current = str(CONFIG.get("ascii_style", "CLASSIC") or "CLASSIC").upper()
        print(f"Current: {current}\n")

        names = list(ASCII_STYLES.keys())
        for i, n in enumerate(names, start=1):
            s = ASCII_STYLES[n]
            print(f"[{i}] {n}    line='{s['line']}' corner='{s['corner']}' fill='{s['fill']}'")
        print("\n[0] Back")

        c = input("> ").strip()
        if c == "0":
            return
        if c.isdigit():
            idx = int(c) - 1
            if 0 <= idx < len(names):
                CONFIG["ascii_style"] = names[idx]
                save_config(CONFIG)
                log_event(f"ASCII style changed to {names[idx]}")
                print("Saved ✅")
                time.sleep(0.6)

def style_tab():
    while True:
        header("TAB 5 — STYLE", "STYLE")
        print(f"Theme: {CONFIG.get('theme_name','RED')} | Logo: {CONFIG.get('logo_name','ZENIK+DUCK')} | ASCII: {CONFIG.get('ascii_style','CLASSIC')}")
        print("""
[1] Change Colors (Theme)
[2] Change Logo
[3] Change ASCII Style (borders)
[4] Preview current Logo
[0] Back
""")
        c = input("> ").strip()
        if c == "1":
            style_change_colors_menu()
        elif c == "2":
            style_change_logo_menu()
        elif c == "3":
            style_change_ascii_menu()
        elif c == "4":
            header("STYLE — LOGO PREVIEW", "STYLE")
            print(get_logo_text())
            pause()
        elif c == "0":
            return
        else:
            print("Invalid.")
            time.sleep(0.6)

# ------------------ Tabs 1 & 2 ------------------
def ip_network_tab():
    while True:
        header("TAB 1 — IP / NETWORK", "IPNET")
        print("""
[1] Local IP
[2] IP Lookup (detailed)
[3] Geo Map (IP location)
[4] Distance (Your IP ↔ Another IP)
[5] Network Overview (local/public + nearby SSIDs)
[6] Wi-Fi Scan (SSID only)
[0] Back
""")
        c = input("> ").strip()

        if c == "1":
            local_ip()
        elif c == "2":
            ip_lookup()
        elif c == "3":
            geo_map()
        elif c == "4":
            distance_tool()
        elif c == "5":
            network_overview()
        elif c == "6":
            wifi_scan_only()
        elif c == "0":
            return
        else:
            print("Invalid option.")
            time.sleep(0.6)

def utilities_tab():
    while True:
        header("TAB 2 — UTILITIES", "UTILS")
        print(f"Webhook: {'SET' if get_webhook_url() else 'NOT SET'} | Config: {CONFIG_FILE} | Logs: {LOG_FILE}")
        print("""
[1] System Info
[2] Ping
[3] Password Generator + Strength
[4] Notes
[5] Vault (Encrypted)
[6] Webhook (saved + embed test)
[7] Settings
[8] View Activity Logs
[0] Back
""")
        c = input("> ").strip()

        if c == "1":
            system_info()
        elif c == "2":
            ping_tool()
        elif c == "3":
            password_generator()
        elif c == "4":
            notes()
        elif c == "5":
            vault_menu()
        elif c == "6":
            webhook_menu()
        elif c == "7":
            settings_menu()
        elif c == "8":
            view_logs()
        elif c == "0":
            return
        else:
            print("Invalid option.")
            time.sleep(0.6)

# ------------------ MAIN MENU ------------------
def main_menu():
    log_event(f"{APP_NAME} started {VERSION}.")
    while True:
        header("", "MAIN")

        # (B) Windows/Mobile main menu handling:
        if is_windows():
            print("""
[1] TAB 1: IP / Network
[2] TAB 2: Utilities
[3] TAB 3: Tools (Windows)
[4] TAB 4: Gaming (Windows)
[5] TAB 5: Style
[0] Exit
""")
        else:
            print("""
[1] TAB 1: IP / Network
[2] TAB 2: Utilities
[3] Tools (Windows-only) — disabled on Mobile/iSH
[4] Gaming (Windows-only) — disabled on Mobile/iSH
[5] TAB 5: Style
[0] Exit
""")

        c = input("> ").strip()

        if c == "1":
            ip_network_tab()
        elif c == "2":
            utilities_tab()
        elif c == "3":
            if not is_windows():
                header("WINDOWS-ONLY TAB", "TOOLS")
                print("Tools tab needs Windows.")
                print("On iPhone/iPad: use iSH for the app, but Windows tools are disabled there.")
                pause()
            else:
                tools_tab()
        elif c == "4":
            if not is_windows():
                header("WINDOWS-ONLY TAB", "GAMING")
                print("Gaming tab needs Windows.")
                pause()
            else:
                gaming_tab()
        elif c == "5":
            style_tab()
        elif c == "0":
            log_event(f"{APP_NAME} exited.")
            clear()
            print(get_accent() + "Exiting ZENIK TOOL..." + RESET)
            time.sleep(0.8)
            break
        else:
            print("Invalid option.")
            time.sleep(0.6)

if __name__ == "__main__":
    main_menu()
