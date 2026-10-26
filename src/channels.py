"""
channels.py
-----------
The Telegram channels and groups this project reads.

telegram_scraper.py fetches exactly these, and listener.py saves messages only
from these. Messages from any other chat, including private chats, are ignored.
To follow a new channel, add its @username to one of the lists below.
"""

from __future__ import annotations


def normalize_channel(raw_channel: str) -> str:
    channel = raw_channel.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if channel.startswith(prefix):
            channel = channel[len(prefix):]
            break
    channel = channel.strip("/")
    return channel if channel.startswith("@") else f"@{channel}"


def dedupe_channels(channels: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for channel in channels:
        normalized = normalize_channel(channel)
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


# ── Regular channels ──────────────────────────────────────────────
REGULAR_CHANNELS = dedupe_channels([
    "@mygojo1",
    "@Roya_King4102",
    "@Temerproperties2m",
    "@ApartmentForYouAyatRealEstate",
    "@apartama_21",
    "@giftrealestateee",
    "@dmcrealestateofficial",
    "@jamborealestate",
    "@brokercom11",
    "@menoriarealestatesalesconsultant",
    "@TemerApartmentShop",
    "@jamborealestat",
    "@onlinegebeyacom",
    "@ET_Creatives_Homes_And_Cars",
    "@houseapartmentcarreleator",
    "@hugeAddisababamarket2025",
    "@realityaddisababa",
    "@livingethio",
    "@Apartments_store",
    "@Apartments_for_rent_Addis_Ababa",
    "@condoaddis",
    "@apartmentsaleboleayatcmckazanchi",
    "@AddisBrokerageNetworking",
    "@Bet_afri",
    "@Betafrivip",            # @Bet_afri sister: 30,000+ ETB rentals
    "@Bet_afri_Business",     # @Bet_afri sister: commercial/office rentals — income approach data
    "@addishomeset",
    "@Addisababagebeya",
    "@ETHIOhouseagents",
    "@smartdealers",
    "@Ethiodelala2",
])

# ── Forum/Topic groups (developer intelligence hubs) ─────────────
FORUM_GROUPS = dedupe_channels([
    "@luxury_freelancers",
    "@championallsites",
])

# Telegram usernames are case-insensitive.
ALLOWED_USERNAMES = {c.lstrip("@").lower() for c in REGULAR_CHANNELS + FORUM_GROUPS}


def is_configured_chat(entity) -> bool:
    """True only for a channel or group whose public @username is listed above."""
    names = [getattr(entity, "username", None)]
    # Some channels have several usernames (Telethon puts the extra ones in .usernames).
    names += [getattr(u, "username", None) for u in (getattr(entity, "usernames", None) or [])]
    return any(n and n.lower() in ALLOWED_USERNAMES for n in names)
