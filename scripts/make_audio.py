import asyncio, json, sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
import re

cfg = json.loads((ROOT / "site" / "config.json").read_text())
VOICES = {"en": cfg.get("voice_en", "en-GB-SoniaNeural"), "it": cfg.get("voice_it", "it-IT-GiuseppeMultilingualNeural")}
data = json.loads((ROOT / "site" / "data" / "latest.json").read_text())
out = ROOT / "site" / "audio" / data["date"]
out.mkdir(parents=True, exist_ok=True)


def text_for(it, lang, full):
    x = it.get("i18n", {}).get("it") if lang == "it" else None
    x = x or it
    parts = [x["title"] + ".", x["summary"]]
    if full:
        parts += x["body"] if len(x["body"]) == len(it["body"]) else it["body"]
    text = "\n\n".join(parts)
    pct, amp = (" per cento", " e ") if lang == "it" else (" percent", " and ")
    text = re.sub(r"(\d)\s?%", lambda m: m.group(1) + pct, text).replace(" & ", amp)
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"[ \t]+", " ", text)


async def one(sem, name, text, lang, done):
    async with sem:
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, VOICES[lang]).save(str(out / name))
                done.append(f"{data['date']}/{name}")
                return
            except Exception as e:
                print("retry", name, e, file=sys.stderr)
                await asyncio.sleep(2 * (attempt + 1))


async def main():
    print("voices", VOICES)
    sem, done, tasks = asyncio.Semaphore(4), [], []
    for it in data["items"]:
        for lang in VOICES:
            if lang == "it" and not it.get("i18n", {}).get("it"):
                continue
            for kind, full in (("s", False), ("f", True)):
                tasks.append(one(sem, f"{it['id']}-{lang}-{kind}.mp3", text_for(it, lang, full), lang, done))
    await asyncio.gather(*tasks)
    (out / "manifest.json").write_text(json.dumps({"files": sorted(done)}))
    print(f"audio: {len(done)}/{len(tasks)} files")


asyncio.run(main())
