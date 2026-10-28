r"""
media_web_fetch.py
------------------
Fetches the photos of the round-2 pilot posts (task S15) from Telegram's PUBLIC web
preview, https://t.me/s/<channel>/<message id>, which needs no Telegram account. The
owner's Telegram login is never used for photos (see CLAUDE.md).

Very slow and polite: one request every 20-40 seconds (random), for pages and photos
alike; at most 50 photos; it stops at the first error or sign of blocking (anything but a
normal answer). A channel without a public preview (forum groups, for example) is skipped
and reported. A page shows about 20 posts, so posts close together share one page request.

Photos go to data/images/web_preview/<channel>_<message id>.jpg (only real JPEG files are
kept); the log of the run to data/media_pilot/web_fetch_log.json. The database is not
changed.

Usage:
    venv\Scripts\python.exe src\media_web_fetch.py
"""

from __future__ import annotations

import html
import json
import random
import re
import time
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parents[1]
PLAN_FILE = BASE_DIR / "data" / "media_pilot" / "round2_plan.json"
OUT_DIR = BASE_DIR / "data" / "images" / "web_preview"
LOG_FILE = BASE_DIR / "data" / "media_pilot" / "web_fetch_log.json"
PAUSE_SECONDS = (20, 40)
MAX_PHOTOS = 50
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130.0 Safari/537.36",
           "Accept-Language": "en"}
# A photo in the preview: <a class="tgme_widget_message_photo_wrap …" style="…background-image:url('<photo
# address>')" … href="https://t.me/<channel>/<id>[?single]"> (the two attributes in either order).
PHOTO_TAG_RE = re.compile(r'<a class="tgme_widget_message_photo_wrap[^>]*>', re.S)
PHOTO_HREF_RE = re.compile(r'href="https://t\.me/([^/"?]+)/(\d+)')
PHOTO_URL_RE = re.compile(r"background-image:url\('([^']+)'\)")


def photos_on_page(page_text: str):
    """(channel, message id, photo address) of every photo on a preview page."""
    for tag in PHOTO_TAG_RE.findall(page_text):
        href, url = PHOTO_HREF_RE.search(tag), PHOTO_URL_RE.search(tag)
        if href and url:
            yield href.group(1), int(href.group(2)), html.unescape(url.group(1))


class Stop(Exception):
    """An error or a sign of blocking: the run ends here."""


class Polite:
    def __init__(self, client):
        self.client, self.requests = client, 0

    def get(self, url):
        if self.requests:
            time.sleep(random.uniform(*PAUSE_SECONDS))
        self.requests += 1
        try:
            response = self.client.get(url)
        except httpx.HTTPError as e:
            raise Stop(f"network error ({type(e).__name__}) on {url}")
        if response.status_code != 200:
            raise Stop(f"{url} answered {response.status_code}")
        return response


def main() -> None:
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # A re-run does not ask again about channels found without a preview, and photos already
    # saved count toward the cap.
    earlier = json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else {}
    no_preview = set(earlier.get("_summary", {}).get("channels without a public preview", []))
    saved = sum(1 for p in plan if (OUT_DIR / p["image"]).exists() and (OUT_DIR / p["image"]).stat().st_size)
    log, photos = {}, {}
    started = time.time()

    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        web = Polite(client)
        try:
            for p in plan:
                key = f"{p['channel_name']}/{p['message_id']}"
                channel, message_id, out = p["channel_name"], p["message_id"], OUT_DIR / p["image"]
                if saved >= MAX_PHOTOS:
                    break
                if out.exists() and out.stat().st_size:
                    log[key] = "already here"
                    continue
                if channel in no_preview:
                    log[key] = "channel has no public preview"
                    continue
                if message_id not in photos.get(channel, {}):
                    page = web.get(f"https://t.me/s/{channel}/{message_id}")
                    if "/s/" not in str(page.url) or "tgme_widget_message" not in page.text:
                        no_preview.add(channel)
                        log[key] = "channel has no public preview"
                        print(f"{key}: no public preview, channel skipped")
                        continue
                    if "Too Many Requests" in page.text:
                        raise Stop(f"Telegram asked us to slow down on {page.url}")
                    found = [f for f in photos_on_page(page.text) if f[0].lower() == channel.lower()]
                    if not found and "tgme_widget_message_photo_wrap" in page.text:
                        raise Stop("the preview page has photos but none could be read: the page layout changed")
                    for _, found_id, address in found:
                        photos.setdefault(channel, {})[found_id] = address
                address = photos.get(channel, {}).get(message_id)
                if not address:
                    log[key] = "no photo for this post in the preview (deleted, or not a photo)"
                    print(f"{key}: no photo in the preview")
                    continue
                photo = web.get(address)
                if not photo.content.startswith(b"\xff\xd8\xff"):
                    log[key] = "not a JPEG file, not kept"
                    continue
                out.write_bytes(photo.content)
                saved += 1
                log[key] = "saved"
                print(f"{key}: saved ({len(photo.content) // 1024} KB), {saved} photos, {web.requests} requests")
        except Stop as e:
            log["_stopped"] = str(e)
            print(f"STOPPED: {e}")

    log["_summary"] = {"photos saved": saved, "requests": web.requests, "minutes": round((time.time() - started) / 60, 1),
                       "channels without a public preview": sorted(no_preview)}
    LOG_FILE.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(log["_summary"])


if __name__ == "__main__":
    main()
