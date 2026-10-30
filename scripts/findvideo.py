import json, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ytsearch import search

TRUSTED = [
    "reuters", "associated press", "ap archive", "bloomberg", "cnbc", "bbc", "dw news", "euronews", "al jazeera", "sky news",
    "sky tg24", "rai news", "rainews", "tg la7", "la7", "ansa", "il sole 24 ore", "corriere", "la repubblica", "skytg24",
    "european commission", "european parliament", "consiglio", "governo", "palazzo chigi", "financial times", "the economist",
    "tldr news", "wired", "the verge", "cnet", "techcrunch", "france 24", "cbs news", "abc news", "nbc news", "pbs newshour",
    "channel 4", "france 24", "dazn", "sport", "gazzetta", "al nassr", "uefa", "espn", "fifa", "nasa", "esa", "agenzia spaziale", "fanpage",
]
STOP = set("the a an and or of to in on for with as at by from is are was were be been after before over under into new says say said "
           "il lo la i gli le un una e o di a da in con su per tra fra che del della dei delle al alla ai alle nel nella sul sulla "
           "ha sono come ma piu anche non si".split())


def toks(s):
    return {w for w in re.findall(r"[a-zàèéìòù0-9]{3,}", s.lower()) if w not in STOP}


def secs(t):
    p = [int(x) for x in re.findall(r"\d+", t or "")]
    if not p or ":" not in (t or ""):
        return 0
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def queries(it):
    it_ = it.get("i18n", {}).get("it", {})
    langs = [("en", it)] + ([("it", {**it, **it_})] if it["sec"] in ("ita", "reg") else [])
    qs = []
    for lang, x in langs:
        words = [w for w in re.findall(r"[\w'’-]+", x["title"]) if w.lower() not in STOP]
        qs.append(" ".join(words[:7]))
        qs.append(" ".join(words[:4]) + (" news" if lang == "en" else " notizie"))
        sw = [w for w in re.findall(r"[\w'’-]+", x["summary"]) if w.lower() not in STOP and w[0].isupper()]
        if sw:
            qs.append(" ".join(dict.fromkeys(sw[:4])))
        caps = [w for w in re.findall(r"[\w'’.-]+", x["title"]) if w[0].isupper() or w[0].isdigit()]
        if len(caps) >= 2:
            qs.append(" ".join(caps[:4]))
        qs.append(" ".join(words[:5]) + (" explained" if lang == "en" else " spiegato"))
        for src in it.get("sources", [])[:3]:
            n = src["n"].split(",")[0]
            if any(t in n.lower() for t in TRUSTED):
                qs.append(f"{n} " + " ".join(words[:4]))
    return list(dict.fromkeys(q for q in qs if q.strip()))


TOPIC = {
    "ai": ["AI news", "artificial intelligence news"],
    "pol": ["Europe politics news", "world news today"],
    "inn": ["science news", "NASA ESA news", "technology innovation news"],
    "biz": ["markets news", "economy news Europe"],
    "lav": ["jobs report news", "labour market news"],
    "vc": ["startup funding news", "venture capital news"],
    "cr7": ["Cristiano Ronaldo", "Al Nassr"],
    "reg": ["EU AI Act explained", "European Parliament artificial intelligence act", "European Commission AI Office", "AI regulation Europe"],
    "ita": ["Italia notizie", "Italy news", "Sky TG24", "Rai News"],
}


def related(it):
    words = [w for w in re.findall(r"[\w'’-]+", it["title"]) if w.lower() not in STOP and not w.isdigit()]
    ref = toks(it["title"] + " " + it["summary"])
    seen, cands = set(), []
    qs = [f"{t} {' '.join(words[:2])}" for t in TOPIC.get(it["sec"], [])] + TOPIC.get(it["sec"], [])
    if it["sec"] == "ita" and it.get("topic"):
        qs += [f"Italia {TOPIC[it['topic']][0]}", f"Italy {TOPIC[it['topic']][1]}"]
    for q in qs:
        try:
            rows = search(q, 10)
        except Exception:
            continue
        for vid, title, chan, length, age, views in rows:
            d = secs(length)
            if vid in seen or d == 0 or d > 600 or re.search(r"[\u0400-\u04ff\u3040-\u30ff\u4e00-\u9fff\u0600-\u06ff\u0900-\u097f]", title):
                continue
            seen.add(vid)
            if not any(t in chan.lower() for t in TRUSTED):
                continue
            ov = len(ref & toks(title)) / max(1, min(len(toks(title)), 8))
            cands.append(dict(vid=vid, title=title, chan=chan, dur=d, age=age, score=round(ov, 2), trusted=True, ov=round(ov, 2), related=True))
    cands.sort(key=lambda c: -c["score"])
    return [c for c in cands[:6] if embeddable(c["vid"])][:2]


def embeddable(vid):
    try:
        q = urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe="")
        urllib.request.urlopen(f"https://www.youtube.com/oembed?url={q}&format=json", timeout=12)
        return True
    except Exception:
        return False


def find(it, rel=False):
    ref = toks(it["title"] + " " + it["summary"])
    seen, cands = set(), []
    for q in queries(it):
        try:
            rows = search(q, 10)
        except Exception:
            continue
        for vid, title, chan, length, age, views in rows:
            if vid in seen:
                continue
            seen.add(vid)
            d = secs(length)
            if d == 0 or d > 900:
                continue
            ov = len(ref & toks(title)) / max(1, min(len(toks(title)), 8))
            if re.search(r"[\u0400-\u04ff\u3040-\u30ff\u4e00-\u9fff\u0600-\u06ff\u0900-\u097f]", title):
                continue
            trusted = any(t in chan.lower() for t in TRUSTED)
            score = ov + (0.25 if trusted and ov >= 0.3 else 0) + (0.05 if d <= 180 else 0)
            if ov < 0.2:
                continue
            cands.append(dict(vid=vid, title=title, chan=chan, dur=d, age=age, score=round(score, 2), trusted=trusted, ov=round(ov, 2)))
    cands.sort(key=lambda c: -c["score"])
    out = []
    for c in cands[:8]:
        if embeddable(c["vid"]):
            out.append(c)
        if len(out) == 3:
            break
    if not out and rel:
        out = related(it)
    return out


def main(path, apply, rel):
    d = json.loads(Path(path).read_text())
    todo = [it for it in d["items"] if not any(m["type"] == "video" for m in it.get("media", []))]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda it: find(it, rel), todo))
    got = 0
    for it, cands in zip(todo, res):
        print(f"\n[{it['id']}] {it['sec']} | {it['title'][:80]}")
        for c in cands:
            print(f"   {c['score']:.2f} ov={c['ov']} {'T' if c['trusted'] else '-'} https://www.youtube.com/watch?v={c['vid']} | {c['title'][:70]} | {c['chan']} | {c['dur']}s | {c['age']}")
        best = next((c for c in cands if not c.get("related") and (c["ov"] >= 0.7 or (c["trusted"] and c["ov"] >= 0.3))), None)
        if not best:
            best = next((c for c in cands if c.get("related")), None)
        if apply and best:
            m = {"type": "video", "u": f"https://www.youtube.com/watch?v={best['vid']}", "cap": ("Related: " if best.get("related") else "") + best["title"], "credit": best["chan"]}
            if best["dur"] > 90:
                m["start"], m["end"] = 8, min(best["dur"] - 2, 50)
            it["media"].insert(0, m)
            it.setdefault("i18n", {}).setdefault("it", {}).setdefault("media_caps", [""] * (len(it["media"]) - 1))
            it["i18n"]["it"]["media_caps"].insert(0, ("Correlato: " if best.get("related") else "") + best["title"])
            got += 1
    have = len(d["items"]) - len(todo)
    print(f"\nalready had video: {have}; applied to {got}/{len(todo)}; total {have + got}/{len(d['items'])}")
    if apply:
        Path(path).write_text(json.dumps(d, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv, "--related" in sys.argv)
