r"""
listener_health.py
------------------
The listener's simple daily health log (Phase 1, ROADMAP.md): for each day (Addis Ababa time), the messages
received from the channels in channels.py, the new ones saved, the listings added, rent rows, repeats removed,
photos/videos/PDFs noted in the media queue, errors, and every warning or stop, with its time and reason.

One file per day in data/listener/health/ (data/ is never committed: the notes name channels, not people).
listener.py and listener_service.py write it; database\scrape_check.py shows it.
"""

from __future__ import annotations

import json
from pathlib import Path

import telegram_safety as safety

HEALTH_DIR = Path(__file__).resolve().parents[1] / "data" / "listener" / "health"
COUNTS = ("received", "saved", "listings_added", "rentals_added", "repeats_removed", "media_queued",
          "errors", "starts", "restarts")


def _path(day: str) -> Path:
    return HEALTH_DIR / f"{day}.json"


def read(day: str | None = None) -> dict:
    day = day or safety.now().date().isoformat()
    try:
        return json.loads(_path(day).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"day": day, **{k: 0 for k in COUNTS}, "notes": []}


def add(**counts) -> None:
    h = read()
    for k, n in counts.items():
        h[k] = h.get(k, 0) + n
    h["last_update"] = safety.now().strftime("%H:%M")
    _write(h)


def note(kind: str, text: str) -> None:
    """kind: "warning" (from Telegram, or a stop), "error" (a message not processed), or "info"."""
    h = read()
    h["notes"].append({"time": safety.now().strftime("%H:%M"), "kind": kind, "text": text[:300]})
    h["notes"] = h["notes"][-200:]
    _write(h)


def _write(h: dict) -> None:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(h["day"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_path(h["day"]))


def summary(day: str | None = None) -> str:
    h = read(day)
    warnings = [n for n in h["notes"] if n["kind"] == "warning"]
    lines = [f"Listener, {h['day']}: {h['received']} messages received, {h['saved']} new saved, "
             f"{h['listings_added']} listings added ({h['rentals_added']} rent rows), {h['repeats_removed']} repeats "
             f"removed, {h['media_queued']} photos/videos/PDFs queued, {h['errors']} errors; "
             f"started {h['starts']} times ({h['restarts']} restarts after a crash); warnings: {len(warnings)}"]
    lines += [f"    {n['time']} {n['kind']}: {n['text']}" for n in h["notes"] if n["kind"] != "info"][-10:]
    return "\n".join(lines)
