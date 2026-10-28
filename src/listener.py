r"""
listener.py
-----------
Real-time Telegram listener. Only messages from the channels and groups in
channels.py are saved; private chats and every other chat are ignored.
  1) Insert raw messages into telegram_listings
  2) Run the valuation/cleaning pipeline to create processed_listings
  3) If the chat is a Forum, use topic_resolver to refine location/type

Account safety (see "Telegram account safety" in CLAUDE.md and telegram_safety.py):
- it uses the existing login file and stops if that is missing or no longer valid; it
  never logs in by itself;
- it never runs at the same time as the scraper (one lock for both);
- it only listens; the one request it makes itself (the title of a forum topic) is made
  once per topic and counts toward the daily cap, after which titles are skipped;
- any warning from Telegram stops it at once and keeps Telegram unused until the next day.

Run:
  venv\Scripts\python.exe src\listener.py      (Ctrl+C stops it)

Env:
  TG_API_ID, TG_API_HASH (required)
  TG_SESSION_NAME (optional; overrides the login file's path)
  DB_PASSWORD and the other DB_* settings come from .env (see settings.py)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine, text
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.functions.messages import GetForumTopicsByIDRequest

import telegram_safety as safety
from run_pipeline import ValuationPipeline
from topic_resolver import resolve_location, resolve_property_type
from processor import parse_forum_topic_title
from advert_classifier import classify_listing
from channels import is_configured_chat
from protection import PARSER_WRITE_SQL
from settings import DB_URL


def channel_url_from_entity(entity) -> str:
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}"
    title = getattr(entity, "title", None) or "unknown"
    return f"tg://chat/{getattr(entity, 'id', 'unknown')}#{title}"


def safe_divide(price, sqm):
    try:
        if price and sqm and sqm >= 1:
            return round(price / sqm, 2)
    except (TypeError, ZeroDivisionError):
        pass
    return None


engine = create_engine(DB_URL)

INSERT_TL_SQL = text("""
    INSERT INTO telegram_listings (
        channel, message_id, text, topic_title, posted_at, has_media,
        has_attachment, attachment_type
    )
    VALUES (
        :channel, :message_id, :text, :topic_title, :posted_at, :has_media,
        :has_attachment, :attachment_type
    )
    ON CONFLICT (channel, message_id) DO NOTHING
    RETURNING id;
""")

SELECT_TL_ID_SQL = text("""
    SELECT id
    FROM telegram_listings
    WHERE channel = :channel AND message_id = :message_id
    LIMIT 1;
""")

INSERT_PROCESSED_SQL = text("""
    INSERT INTO processed_listings (
        id, listing_status, intent, listing_class,
        valuation_eligible, sale_analytics_eligible, developer_analytics_eligible,
        property_type, property_subtype, location, city,
        plot_sqm, builtup_sqm,
        bedrooms, bathrooms,
        sale_price_birr, rent_price_birr, rent_advance_birr,
        payment_type, bank_loan_pct, down_payment_pct,
        finish_state, developer,
        price_currency, price_usd, floor_level,
        contact_phone, contact_username,
        price_per_builtup_sqm, price_per_plot_sqm,
        confidence_json, source_channel, raw_text, posted_at
    )
    VALUES (
        :id, :listing_status, :intent, :listing_class,
        :valuation_eligible, :sale_analytics_eligible, :developer_analytics_eligible,
        :property_type, :property_subtype, :location, :city,
        :plot_sqm, :builtup_sqm,
        :bedrooms, :bathrooms,
        :sale_price_birr, :rent_price_birr, :rent_advance_birr,
        :payment_type, :bank_loan_pct, :down_payment_pct,
        :finish_state, :developer,
        :price_currency, :price_usd, :floor_level,
        :contact_phone, :contact_username,
        :price_per_builtup_sqm, :price_per_plot_sqm,
        :confidence_json, :source_channel, :raw_text, :posted_at
    )
    ON CONFLICT (id) DO NOTHING;
""")

UPSERT_FORUM_PROJECT_SQL = text("""
    INSERT INTO processed_listings (
        id, listing_status, intent, listing_class,
        valuation_eligible, sale_analytics_eligible, developer_analytics_eligible,
        property_type, property_subtype, location, city,
        plot_sqm, builtup_sqm,
        bedrooms, bathrooms,
        sale_price_birr, rent_price_birr, rent_advance_birr,
        payment_type, bank_loan_pct, down_payment_pct,
        finish_state, developer,
        price_currency, price_usd, floor_level,
        contact_phone, contact_username,
        price_per_builtup_sqm, price_per_plot_sqm,
        confidence_json, source_channel, raw_text, posted_at
    )
    VALUES (
        :id, :listing_status, :intent, :listing_class,
        :valuation_eligible, :sale_analytics_eligible, :developer_analytics_eligible,
        :property_type, :property_subtype, :location, :city,
        :plot_sqm, :builtup_sqm,
        :bedrooms, :bathrooms,
        :sale_price_birr, :rent_price_birr, :rent_advance_birr,
        :payment_type, :bank_loan_pct, :down_payment_pct,
        :finish_state, :developer,
        :price_currency, :price_usd, :floor_level,
        :contact_phone, :contact_username,
        :price_per_builtup_sqm, :price_per_plot_sqm,
        :confidence_json, :source_channel, :raw_text, :posted_at
    )
    ON CONFLICT (id) DO UPDATE
    SET
        listing_status = CASE
            WHEN EXCLUDED.listing_status = 'INACTIVE' THEN 'INACTIVE'
            ELSE COALESCE(processed_listings.listing_status, EXCLUDED.listing_status)
        END,
        sale_price_birr = COALESCE(processed_listings.sale_price_birr, EXCLUDED.sale_price_birr),
        rent_price_birr = COALESCE(processed_listings.rent_price_birr, EXCLUDED.rent_price_birr),
        builtup_sqm = COALESCE(processed_listings.builtup_sqm, EXCLUDED.builtup_sqm),
        plot_sqm = COALESCE(processed_listings.plot_sqm, EXCLUDED.plot_sqm),
        property_type = CASE
            WHEN processed_listings.property_type IS NULL OR processed_listings.property_type = 'UNKNOWN'
            THEN COALESCE(EXCLUDED.property_type, processed_listings.property_type)
            ELSE processed_listings.property_type
        END,
        location = CASE
            WHEN processed_listings.location = 'other_addis'
            THEN COALESCE(EXCLUDED.location, processed_listings.location)
            ELSE processed_listings.location
        END,
        city = COALESCE(processed_listings.city, EXCLUDED.city),
        developer = COALESCE(processed_listings.developer, EXCLUDED.developer),
        finish_state = COALESCE(processed_listings.finish_state, EXCLUDED.finish_state),
        posted_at = GREATEST(processed_listings.posted_at, EXCLUDED.posted_at),
        raw_text = CASE
            WHEN EXCLUDED.sale_price_birr IS NOT NULL THEN EXCLUDED.raw_text
            ELSE processed_listings.raw_text
        END;
""")

UPDATE_PROCESSED_FROM_TOPIC_SQL = text("""
    UPDATE processed_listings
    SET
        location = COALESCE(:location, location),
        city = COALESCE(:city, city),
        property_type = COALESCE(:property_type, property_type)
    WHERE id = :id
      AND (location = 'other_addis' OR property_type IS NULL OR property_type = 'UNKNOWN');
""")


async def get_forum_topic_title(client: TelegramClient, budget: safety.DailyBudget, titles: dict,
                                entity, msg) -> Optional[str]:
    """The forum topic's title, asked from Telegram once per topic (a warning is passed on)."""
    topic_id = getattr(msg, "reply_to_top_id", None)
    if not topic_id and getattr(msg, "reply_to", None):
        topic_id = getattr(msg.reply_to, "reply_to_top_id", None)
    if not topic_id:
        return None

    key = (getattr(entity, "id", None), int(topic_id))
    if key not in titles:
        if not budget.can_spend():
            return None   # today's request limit is used up: the message is saved without its topic
        budget.spend()
        try:
            result = await client(GetForumTopicsByIDRequest(peer=entity, topics=[int(topic_id)]))
        except (OSError, asyncio.TimeoutError):
            return None
        topics = getattr(result, "topics", None) or []
        titles[key] = getattr(topics[0], "title", None) if topics else None
    return titles[key]


def resolve_from_topic(topic_title: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    loc, city = resolve_location(topic_title)
    ptype = resolve_property_type(topic_title)
    return loc, city, ptype


async def listen(session: Path, api_id: int, api_hash: str, budget: safety.DailyBudget) -> None:
    pipeline = ValuationPipeline()

    # Schema safety: add attachment columns if missing
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS has_attachment BOOLEAN DEFAULT false;"))
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS attachment_type TEXT;"))
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS reply_to_top_id BIGINT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS listing_status TEXT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS rent_price_birr BIGINT;"))

    client = TelegramClient(str(session.with_suffix("")), api_id, api_hash,
                            flood_sleep_threshold=safety.FLOOD_SLEEP_THRESHOLD)
    topic_titles: dict = {}   # (chat id, topic id) -> title: each topic is asked for once
    stops: list = []          # the stop a message ran into, if any

    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        if stops:
            return
        try:
            await save_message(event)
        except RPCError as e:
            if isinstance(e, safety.CHANNEL_PROBLEMS):
                return
            stops.append(safety.stop_after_warning(budget, e, "while the listener was running"))
            asyncio.get_running_loop().create_task(client.disconnect())   # ends run_until_disconnected

    async def save_message(event: events.NewMessage.Event) -> None:
        msg = event.message
        # Privacy: save nothing from private chats or from chats not in channels.py.
        if not msg or event.is_private:
            return

        entity = getattr(event, "chat", None)
        if entity is None:   # not sent along with the message: asking for it is a request
            if not budget.can_spend():
                print("Today's request limit is used up: a message from an unknown chat was not saved.")
                return
            budget.spend()
            try:
                entity = await event.get_chat()
            except (OSError, asyncio.TimeoutError, ValueError):
                return
        if not is_configured_chat(entity):
            return

        has_attachment = bool(getattr(msg, "photo", None) or getattr(msg, "document", None))
        has_media = has_attachment

        attachment_type: Optional[str] = None
        pdf_filename: Optional[str] = None
        if getattr(msg, "photo", None):
            attachment_type = "IMAGE"
        elif getattr(msg, "document", None):
            mime = (getattr(getattr(msg.document, "mime_type", None), "lower", lambda: "")() or "").lower()
            if "pdf" in mime:
                attachment_type = "PDF"
                pdf_filename = getattr(getattr(msg, "file", None), "name", None)
            elif mime.startswith("video/"):
                attachment_type = "VIDEO"
            else:
                attachment_type = "DOCUMENT"

        text_content = msg.message or ""
        if not text_content and has_attachment:
            # Keep a searchable placeholder. If it's a PDF, include filename.
            if pdf_filename:
                text_content = f"[PDF ONLY] {pdf_filename}"
            else:
                text_content = "[MEDIA ONLY]"
        if not text_content and not has_attachment:
            return

        channel = channel_url_from_entity(entity)

        # Step 1: write raw message to telegram_listings
        with engine.begin() as conn:
            tl_id = conn.execute(INSERT_TL_SQL, {
                "channel": channel,
                "message_id": msg.id,
                "text": text_content,
                "topic_title": None,  # filled below for forum chats when possible
                "posted_at": getattr(msg, "date", None),
                "has_media": has_media,
                "has_attachment": has_attachment,
                "attachment_type": (f"PDF:{pdf_filename}" if attachment_type == "PDF" and pdf_filename else attachment_type),
            }).scalar()

            if tl_id is None:
                tl_id = conn.execute(SELECT_TL_ID_SQL, {
                    "channel": channel,
                    "message_id": msg.id,
                }).scalar()

        if tl_id is None:
            return

        # If forum: fetch topic title and store it back to telegram_listings
        topic_title: Optional[str] = None
        is_forum = bool(getattr(entity, "forum", False))
        reply_to_top_id: Optional[int] = getattr(msg, "reply_to_top_id", None)
        if not reply_to_top_id and getattr(msg, "reply_to", None):
            reply_to_top_id = getattr(msg.reply_to, "reply_to_top_id", None)
        if is_forum:
            topic_title = await get_forum_topic_title(client, budget, topic_titles, entity, msg)
            if topic_title:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE telegram_listings
                        SET topic_title = :topic_title
                        WHERE id = :id
                    """), {"topic_title": topic_title, "id": tl_id})

        if reply_to_top_id is not None:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE telegram_listings SET reply_to_top_id = :tid WHERE id = :id"),
                    {"tid": int(reply_to_top_id), "id": tl_id},
                )

        # Step 2: cleaning pipeline -> processed_listings
        processed_id = str(tl_id)
        if is_forum and reply_to_top_id is not None:
            processed_id = f"{channel}::topic::{int(reply_to_top_id)}"

        record = {"id": processed_id, "text": text_content, "extracted_area": None,
                  "source_channel": channel}
        # Classify before processing — skip adverts entirely
        msg_class = classify_listing(text_content, topic_title)
        if msg_class == "ADVERT":
            return  # drop silently, don't insert into DB
        try:
            result = pipeline.process(record)
        except Exception:
            return

        price_per_built = safe_divide(result.get("sale_price_birr"), result.get("builtup_sqm"))
        price_per_plot = safe_divide(result.get("sale_price_birr"), result.get("plot_sqm"))

        # For forum topics, switch to project-based UPSERT.
        with engine.begin() as conn:
            conn.execute(text(PARSER_WRITE_SQL))
            # Media-only posts are filterable: the parser gives them
            # listing_class MEDIA_PENDING, as the ETL does.
            property_type = result.get("property_type")

            payload = {
                "id": result["id"],
                "listing_status": result.get("listing_status"),
                "intent": result.get("intent"),
                "listing_class": result.get("listing_class"),
                "valuation_eligible": result.get("valuation_eligible"),
                "sale_analytics_eligible": result.get("sale_analytics_eligible"),
                "developer_analytics_eligible": result.get("developer_analytics_eligible"),
                "property_type": property_type,
                "property_subtype": result.get("property_subtype"),
                "location": result.get("location"),
                "city": result.get("city"),
                "plot_sqm": result.get("plot_sqm"),
                "builtup_sqm": result.get("builtup_sqm"),
                "bedrooms": result.get("bedrooms"),
                "bathrooms": result.get("bathrooms"),
                "sale_price_birr": result.get("sale_price_birr"),
                "rent_price_birr": result.get("rent_price_birr"),
                "rent_advance_birr": result.get("rent_advance_birr"),
                "payment_type": result.get("payment_type"),
                "bank_loan_pct": result.get("bank_loan_pct"),
                "down_payment_pct": result.get("down_payment_pct"),
                "finish_state": result.get("finish_state"),
                "developer": result.get("developer"),
                "price_currency": result.get("price_currency"),
                "price_usd": result.get("price_usd"),
                "floor_level": result.get("floor_level"),
                "contact_phone": result.get("contact_phone"),
                "contact_username": result.get("contact_username"),
                "price_per_builtup_sqm": price_per_built,
                "price_per_plot_sqm": price_per_plot,
                "confidence_json": json.dumps(result.get("confidence", {})),
                "source_channel": channel,
                "raw_text": text_content[:2000],
                "posted_at": getattr(msg, "date", None),
            }

            if is_forum and reply_to_top_id is not None:
                # Enrich from topic title where possible.
                if topic_title:
                    meta = parse_forum_topic_title(topic_title)
                    if meta.get("developer_name") and not payload.get("developer"):
                        payload["developer"] = meta["developer_name"]
                    if meta.get("completion_pct") is not None and not payload.get("finish_state"):
                        payload["finish_state"] = f"completion_{meta['completion_pct']}%"
                conn.execute(UPSERT_FORUM_PROJECT_SQL, payload)
            else:
                conn.execute(INSERT_PROCESSED_SQL, payload)

        # Step 3: forum-topic resolver -> update processed_listings
        if is_forum and topic_title:
            loc, city, ptype = resolve_from_topic(topic_title)
            if loc or city or ptype:
                with engine.begin() as conn:
                    conn.execute(UPDATE_PROCESSED_FROM_TOPIC_SQL, {
                        "id": str(tl_id),
                        "location": loc,
                        "city": city,
                        "property_type": ptype,
                    })

    try:
        await safety.connect_with_existing_login(client, budget)
        print("Listening for new messages... (Ctrl+C stops the listener)")
        await client.run_until_disconnected()
    except RPCError as e:
        raise safety.stop_after_warning(budget, e, "while the listener was running")
    except (OSError, asyncio.TimeoutError) as e:
        raise safety.SafetyStop(f"The connection to Telegram was lost ({type(e).__name__}): the listener "
                                "stopped. Start it again later.")
    finally:
        await client.disconnect()
    if stops:
        raise stops[0]
    print("Disconnected from Telegram: the listener stopped.")


async def main() -> int:
    try:
        session = safety.require_session_file()   # before anything else: no login file, no listener
        api_id, api_hash = safety.api_credentials()
        with safety.TelegramLock("listener"):
            budget = safety.DailyBudget()
            budget.check_not_blocked()
            await listen(session, api_id, api_hash, budget)
    except safety.SafetyStop as e:
        print(f"\nSTOPPED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nListener stopped (Ctrl+C).")
