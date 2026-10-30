import json, os, sys, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NAMES_IT = {"ita": "Italia", "reg": "Regolazione AI: UE e Italia", "ai": "AI e Tecnologia", "pol": "Politica e Geopolitica", "inn": "Innovazione", "biz": "Business, Economia e Finanza", "lav": "Mercato del lavoro", "vc": "Venture Capital", "cr7": "Cristiano Ronaldo"}
NAMES = {
    "ita": "Italy",
    "reg": "AI Regulation: EU & Italy",
    "ai": "AI & Technology",
    "pol": "Politics & Geopolitics",
    "inn": "Innovation",
    "biz": "Business, Economy & Finance",
    "lav": "Labour Market",
    "vc": "Venture Capital",
    "cr7": "Cristiano Ronaldo",
}
def skip(msg):
    print(msg)
    sys.exit(0)


force = "--force" in sys.argv
dry = "--dry-run" in sys.argv

cfg = json.loads((ROOT / "site" / "config.json").read_text())
state_path = ROOT / "state" / "sent.json"
state = json.loads(state_path.read_text()) if state_path.exists() else {}
now = datetime.now(ZoneInfo(cfg["timezone"]))
today = now.strftime("%Y-%m-%d")

if not force:
    if not cfg["telegram_enabled"]:
        skip("telegram disabled")
    if now.strftime("%H:%M") < cfg["send_time"]:
        skip("too early")
    if state.get("last_sent") == today:
        skip("already sent")

data_path = ROOT / "site" / "data" / f"{today}.json"
if not data_path.exists():
    skip(f"no briefing for {today} yet")
data = json.loads(data_path.read_text())
lang = cfg.get("telegram_language", "en")
it_ = lang == "it"
names = NAMES_IT if it_ else NAMES
read_word, open_word = ("Leggi", "Apri il resoconto completo") if it_ else ("Read", "Open the full briefing")


def title_of(i):
    return (i.get("i18n", {}).get("it", {}).get("title") if it_ else None) or i["title"]


date_label = (data.get("i18n", {}).get("it", {}).get("date_label") if it_ else None) or data["date_label"]

esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
base = cfg["site_url"].rstrip("/")
lines = [f"<b>Daily News</b> · {esc(date_label)}", ""]
for sec, name in names.items():
    if not cfg["sections"].get(sec):
        continue
    items = [i for i in data["items"] if i["sec"] == sec]
    if not items:
        continue
    lines.append(f"<b>{esc(name)}</b>")
    lines += [f"• {esc(title_of(i))}" for i in items[:2]]
    lines.append(f'<a href="{base}/?d={today}&s={sec}">{read_word} {esc(name)} →</a>')
    lines.append("")
lines.append(f'<a href="{base}/?d={today}">{open_word}</a>')
text = "\n".join(lines)

if dry:
    print(text)
    sys.exit(0)

payload = urllib.parse.urlencode({
    "chat_id": os.environ["TELEGRAM_CHAT_ID"],
    "text": text,
    "parse_mode": "HTML",
    "disable_web_page_preview": "true",
}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage", payload
)
urllib.request.urlopen(req, timeout=30).read()
if not force:
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text(json.dumps({"last_sent": today}))
print("sent", today)
