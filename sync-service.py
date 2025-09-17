#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import re
from datetime import datetime
from telethon import TelegramClient, events
import motor.motor_asyncio

# Configuration
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")  # Optional: Use string session
DB_CHANNEL = int(os.environ.get("DB_CHANNEL", "0"))
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "movie_bot")

# Setup logging
logging.basicConfig(level=logging.INFO)

# MongoDB connection
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DATABASE_NAME]
movies = db.movies

# Telethon client
if SESSION_STRING:
    client = TelegramClient("sync_service", API_ID, API_HASH, session=SESSION_STRING)
else:
    client = TelegramClient("sync_service", API_ID, API_HASH)

def extract_movie_info(text):
    """Extract movie information from message text"""
    if not text:
        return None

    lines = text.split('\n')
    title = lines[0].strip() if lines else "Unknown"

    # Clean title
    title = re.sub(r'[^\w\s\-\.\(\)]', ' ', title).strip()

    # Extract year
    year_match = re.search(r'(19|20)\d{2}', text)
    year = year_match.group() if year_match else None

    # Extract quality
    quality = None
    if 'WEB-DL' in text.upper() or 'WEB DL' in text.upper():
        quality = 'WEB-DL'
    elif 'BLURAY' in text.upper() or 'BDR' in text.upper():
        quality = 'BluRay'
    elif 'HDTS' in text.upper():
        quality = 'HDTS'
    elif 'CAM' in text.upper():
        quality = 'CAM'

    # Extract categories
    categories = []
    text_upper = text.upper()

    if any(keyword in text_upper for keyword in ['HOLLYWOOD', 'ENGLISH']):
        categories.append('hollywood')
    if any(keyword in text_upper for keyword in ['BOLLYWOOD', 'HINDI']):
        categories.append('bollywood')
    if any(keyword in text_upper for keyword in ['ANIME', 'JAPANESE']):
        categories.append('anime')
    if any(keyword in text_upper for keyword in ['WEBSERIES', 'WEB SERIES', 'SERIES']):
        categories.append('webseries')
    if any(keyword in text_upper for keyword in ['TOLLYWOOD', 'TELUGU', 'TAMIL']):
        categories.append('tollywood')
    if any(keyword in text_upper for keyword in ['CARTOON', 'ANIMATION']):
        categories.append('cartoon')

    # Default category if none found
    if not categories:
        if 'S0' in text_upper and 'E0' in text_upper:  # Series pattern
            categories.append('webseries')
        else:
            categories.append('hollywood')  # Default

    # Create slug
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')

    return {
        'slug': slug,
        'title': title,
        'year': year,
        'quality': quality,
        'categories': categories,
        'added_at': datetime.now()
    }

@client.on(events.NewMessage(chats=DB_CHANNEL))
async def handle_new_message(event):
    """Handle new messages in database channel"""
    try:
        message = event.message

        # Skip if no text/caption
        text = message.text or message.caption
        if not text:
            return

        # Extract movie info
        movie_info = extract_movie_info(text)
        if not movie_info:
            return

        # Add message info
        movie_info['tg_message_id'] = message.id
        movie_info['tg_channel_id'] = DB_CHANNEL

        # Extract poster URL if available
        if message.photo:
            movie_info['poster_url'] = f"https://t.me/c/{str(DB_CHANNEL)[4:]}/{message.id}"

        # Get file size
        if message.document:
            movie_info['file_size'] = message.document.size
            movie_info['file_type'] = 'document'
        elif message.video:
            movie_info['file_size'] = message.video.size
            movie_info['file_type'] = 'video'

        # Update MongoDB
        await movies.update_one(
            {'slug': movie_info['slug']},
            {'$set': movie_info},
            upsert=True
        )

        logging.info(f"✅ Updated: {movie_info['title']}")

    except Exception as e:
        logging.error(f"❌ Error processing message: {e}")

async def main():
    """Main function"""
    await client.start()
    me = await client.get_me()
    logging.info(f"🚀 Sync service started: {me.first_name}")

    # Keep running
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
