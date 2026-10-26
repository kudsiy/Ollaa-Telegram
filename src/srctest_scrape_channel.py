from telethon import TelegramClient

from settings import TG_API_ID, TG_API_HASH

api_id = int(TG_API_ID)
api_hash = TG_API_HASH

channel = "ETHIOhouseagents"

async def main():
    async with TelegramClient("session", api_id, api_hash) as client:
        messages = await client.get_messages(channel, limit=20)

        for msg in messages:
            print("="*50)
            print("DATE:", msg.date)
            print("TEXT:", msg.text)

import asyncio
asyncio.run(main())