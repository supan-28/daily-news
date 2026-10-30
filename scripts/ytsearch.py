import json, re, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def walk(o, out):
    if isinstance(o, dict):
        v = o.get("videoRenderer")
        if v and v.get("videoId"):
            out.append(v)
        for x in o.values():
            walk(x, out)
    elif isinstance(o, list):
        for x in o:
            walk(x, out)


def search(q, n=8):
    url = "https://www.youtube.com/results?hl=en&sp=EgIIAw%253D%253D&search_query=" + urllib.parse.quote(q)  # sp: last week
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    m = re.search(r"ytInitialData\s*=\s*(\{.*?\});</script>", html, re.S)
    if not m:
        return []
    out = []
    walk(json.loads(m.group(1)), out)
    rows = []
    for v in out[:n]:
        g = lambda k: (v.get(k, {}).get("simpleText") or "".join(r.get("text", "") for r in v.get(k, {}).get("runs", [])))
        rows.append((v["videoId"], g("title"), g("ownerText"), g("lengthText"), g("publishedTimeText"), g("viewCountText")))
    return rows


if __name__ == "__main__":
    for q in sys.argv[1:]:
        print("##", q)
        try:
            for r in search(q):
                print(f"https://www.youtube.com/watch?v={r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}")
        except Exception as e:
            print("ERROR", e)
