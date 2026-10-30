import json, os, re, shutil, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
KEY = os.environ.get("PEXELS_API_KEY", "")
DEFAULT = {
    "ai": ["artificial intelligence", "robot", "technology", "computer", "data"],
    "reg": ["government", "law", "technology"],
    "pol": ["government", "parliament", "city street"],
    "inn": ["science laboratory", "laboratory", "science", "space"],
    "biz": ["stock market", "finance", "business"],
    "lav": ["office workers", "factory workers", "job interview", "business"],
    "vc": ["startup office", "finance", "business", "technology"],
    "cr7": ["football stadium", "soccer", "stadium crowd"],
    "ita": ["Italy city", "Rome", "Milan"],
}
TOPIC_DEFAULT = {"ai": "technology", "pol": "government", "inn": "science", "biz": "stock market", "lav": "office workers", "vc": "startup", "cr7": "soccer", "reg": "law"}


def get(url, headers=None, binary=False, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    data = urllib.request.urlopen(req, timeout=timeout).read()
    return data if binary else data.decode("utf-8", "ignore")


def pexels(q):
    if not KEY:
        return []
    out = []
    for orient in ("portrait", "landscape"):
        url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": q, "orientation": orient, "size": "medium", "per_page": 12})
        try:
            data = json.loads(get(url, {"Authorization": KEY}))
        except Exception:
            continue
        for v in data.get("videos", []):
            if not 4 <= v.get("duration", 0) <= 45:
                continue
            files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and 500 <= (f.get("width") or 0) <= 1100]
            if not files:
                continue
            f = sorted(files, key=lambda f: f["width"])[0]
            out.append(dict(id=f"px{v['id']}", url=f["link"], author=(v.get("user") or {}).get("name", "Pexels"), credit=f"{(v.get('user') or {}).get('name', '')} / Pexels".strip(" /"), page=v.get("url", "")))
        if len(out) >= 3:
            break
    return out


def mixkit(q):
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
    ids = []
    for path in (f"{slug}/", f"discover/{slug}/"):
        try:
            html = get("https://mixkit.co/free-stock-video/" + path)
        except Exception:
            continue
        ids = list(dict.fromkeys(re.findall(r"https://assets\.mixkit\.co/videos/(\d+)/\1-720\.mp4", html)))
        if ids:
            break
    return [dict(id=f"mk{i}", url=f"https://assets.mixkit.co/videos/{i}/{i}-720.mp4", author="Mixkit", credit="Mixkit", page=f"https://mixkit.co/free-stock-video/") for i in ids]


def transcode(src, dst):
    if not shutil.which("ffmpeg"):
        shutil.copy(src, dst)
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", "14", "-an",
           "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "29", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, timeout=240)


def main():
    data = json.loads((ROOT / "site" / "data" / "latest.json").read_text())
    out = ROOT / "site" / "loops" / data["date"]
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    old = json.loads(mpath.read_text()) if mpath.exists() else {}
    manifest, used = {}, set()
    for it in data["items"]:
        k = str(it["id"])
        q0 = (it.get("loop_query") or "").strip()
        if k in old and old[k].get("q0") == q0 and (out / old[k]["f"]).exists():
            manifest[k] = old[k]
            used.add(old[k]["vid"])
    for it in data["items"]:
        k = str(it["id"])
        if k in manifest:
            continue
        q0 = (it.get("loop_query") or "").strip()
        qs = ([q0] if q0 else []) + DEFAULT.get(it["sec"], []) + ([TOPIC_DEFAULT[it["topic"]]] if it.get("topic") in TOPIC_DEFAULT else [])
        done = False
        for q in qs:
            for src in (pexels, mixkit):
                for c in src(q):
                    if c["id"] in used:
                        continue
                    try:
                        raw = out / f"{k}.raw.mp4"
                        raw.write_bytes(get(c["url"], binary=True, timeout=90))
                        if raw.stat().st_size > 30_000_000:
                            raw.unlink()
                            continue
                        transcode(raw, out / f"{k}.mp4")
                        raw.unlink()
                    except Exception as e:
                        print("skip", c["id"], e, file=sys.stderr)
                        continue
                    manifest[k] = dict(f=f"{k}.mp4", vid=c["id"], credit=c["credit"], page=c["page"], q=q, q0=q0)
                    used.add(c["id"])
                    done = True
                    break
                if done:
                    break
            if done:
                break
        print(f"[{k}] {it['sec']} {'OK ' + manifest[k]['vid'] + ' (' + manifest[k]['q'] + ')' if done else 'none'}")
    for f in out.glob("*.mp4"):
        if f.stem not in manifest:
            f.unlink()
    mpath.write_text(json.dumps(manifest))
    print(f"loops: {len(manifest)}/{len(data['items'])}")


main()
