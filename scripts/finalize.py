import json, re, sys, shutil, urllib.request, urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
CHECK = "--check-media" in sys.argv
SECS = {"ita", "reg", "ai", "pol", "inn", "biz", "lav", "vc", "cr7"}


def fail(msg):
    sys.exit(f"INVALID: {msg}")


def url_ok(u):
    return isinstance(u, str) and re.match(r"https?://[^\s]+$", u) is not None


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def normalize(it):
    media = list(it.get("media") or [])
    if it.get("img"):
        media.append({"type": "image", **it.pop("img")})
    if it.get("video"):
        v = it.pop("video")
        media.append({"type": "video", "u": v["u"], "cap": v.get("title", ""), "credit": v.get("credit", "")})
    it["media"] = media


def media_ok(m):
    try:
        if m["type"] == "video":
            if re.search(r"youtube\.com|youtu\.be", m["u"]):
                q = urllib.parse.quote(m["u"], safe="")
                urllib.request.urlopen(f"https://www.youtube.com/oembed?url={q}&format=json", timeout=15)
                return True
            r = urllib.request.urlopen(urllib.request.Request(m["u"], headers={"User-Agent": UA}), timeout=15)
            return r.status < 400
        r = urllib.request.urlopen(urllib.request.Request(m["u"], headers={"User-Agent": UA}), timeout=15)
        return r.headers.get("content-type", "").startswith("image/")
    except Exception:
        return False


def check_it(d, it, i):
    x = it.get("i18n", {}).get("it")
    if not x:
        fail(f"item {i}: missing i18n.it (Italian translation)")
    for k in ("title", "summary", "ctx"):
        if not x.get(k):
            fail(f"item {i}: i18n.it.{k}")
    if len(x.get("body", [])) != len(it["body"]):
        fail(f"item {i}: i18n.it.body must have {len(it['body'])} paragraphs")
    ck = x.get("checks", [])
    if len(ck) != len(it["checks"]) or not all(c.get("c") and c.get("n") for c in ck):
        fail(f"item {i}: i18n.it.checks must match checks one to one")
    if len(x.get("media_caps", [])) != len(it["media"]):
        fail(f"item {i}: i18n.it.media_caps must match media one to one")


def validate(d, enabled):
    if not re.match(r"\d{4}-\d{2}-\d{2}$", d.get("date", "")):
        fail("date")
    if not d.get("date_label"):
        fail("date_label")
    if not d.get("i18n", {}).get("it", {}).get("date_label"):
        fail("i18n.it.date_label")
    items = d.get("items")
    if not items:
        fail("no items")
    ids = set()
    for it in items:
        i = it.get("id")
        if i in ids or not isinstance(i, int):
            fail(f"bad/duplicate id {i}")
        ids.add(i)
        if it.get("sec") not in SECS:
            fail(f"item {i}: sec")
        if it["sec"] == "ita" and it.get("topic") not in SECS - {"ita"}:
            fail(f"item {i}: Italy items need topic = ai|pol|inn|biz|lav|vc|cr7")
        for k in ("title", "summary", "ctx"):
            if not it.get(k):
                fail(f"item {i}: {k}")
        if len(it.get("body", [])) < 3:
            fail(f"item {i}: body needs >=3 paragraphs")
        src = it.get("sources", [])
        if len(src) < 2:
            fail(f"item {i}: needs >=2 sources")
        for s in src:
            if not (s.get("n") and s.get("t") and url_ok(s.get("u"))):
                fail(f"item {i}: bad source {s}")
        if not it.get("checks"):
            fail(f"item {i}: checks")
        for c in it["checks"]:
            if c.get("s") not in ("ok", "warn", "ko") or not c.get("c") or not c.get("n"):
                fail(f"item {i}: bad check {c}")
        normalize(it)
        if not it["media"]:
            fail(f"item {i}: needs at least 1 media (image or video)")
        for m in it["media"]:
            if m.get("type") not in ("image", "video") or not url_ok(m.get("u")) or not m.get("cap"):
                fail(f"item {i}: bad media {m}")
            if CHECK and not media_ok(m):
                fail(f"item {i}: media not loadable (use another): {m['u']}")
        if not it.get("loop_query"):
            print(f"WARNING: item {i} has no loop_query (feed stock footage will use a generic one)")
        check_it(d, it, i)
        if len(it["media"]) < 2:
            print(f"WARNING: item {i} has only {len(it['media'])} media; aim for 3+")
    nv = sum(any(m["type"] == "video" for m in it["media"]) for it in items)
    print(f"videos: {nv}/{len(items)} stories ({100 * nv // len(items)}%), target 80%")
    if CHECK and nv < 0.7 * len(items) and "--allow-low-video" not in sys.argv:
        fail(f"only {nv}/{len(items)} stories have a video; run scripts/findvideo.py --apply --related, search by hand for the rest, then rerun (minimum 70%)")
    present = {it["sec"] for it in items}
    missing = [s for s in enabled if s not in present]
    if missing:
        fail(f"enabled sections without items: {missing}")


def main(path):
    d = json.loads(Path(path).read_text())
    cfg = json.loads((ROOT / "site" / "config.json").read_text())
    validate(d, [k for k, v in cfg["sections"].items() if v])
    out = DATA / f"{d['date']}.json"
    out.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    shutil.copy(out, DATA / "latest.json")
    dates = sorted((p.stem for p in DATA.glob("20*.json")), reverse=True)
    (DATA / "index.json").write_text(json.dumps(dates))
    print(f"OK {d['date']}: {len(d['items'])} items")


if __name__ == "__main__":
    main(next((a for a in sys.argv[1:] if not a.startswith("--")), DATA / f"{date.today()}.json"))
