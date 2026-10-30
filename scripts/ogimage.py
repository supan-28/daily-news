import re, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def main(page):
    req = urllib.request.Request(page, headers={"User-Agent": UA, "Accept-Language": "en"})
    html = urllib.request.urlopen(req, timeout=15).read(400_000).decode("utf-8", "ignore")
    for prop in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
        for m in re.finditer(r"<meta\b[^>]*>", html, re.I):
            tag = m.group(0)
            if re.search(rf'(?:property|name)=["\']{prop}["\']', tag, re.I):
                c = re.search(r'content=["\']([^"\']+)', tag, re.I)
                if c:
                    return urllib.parse.urljoin(page, c.group(1).replace("&amp;", "&"))
    return None


if __name__ == "__main__":
    for u in sys.argv[1:]:
        try:
            print(u, "->", main(u) or "NONE")
        except Exception as e:
            print(u, "-> ERROR", e)
