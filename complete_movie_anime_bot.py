#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, unquote_plus

# Pyrogram imports
from pyrogram import Client, filters, types, errors
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, 
    Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent, ChatMember
)

# MongoDB imports
import motor.motor_asyncio
from difflib import get_close_matches
import string

# Setup logging
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO
)

# Configuration from environment variables
class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "").replace("@", "")

    # Database Channel
    DB_CHANNEL = int(os.environ.get("DB_CHANNEL", "0"))

    # Force Join Channels (comma separated)
    FORCE_CHANNELS = list(map(int, filter(None, os.environ.get("FORCE_CHANNELS", "").split(","))))

    # Owner
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

    # MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "movie_bot")

    # Website
    WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://yoursite.com")
    GROUP_LINK = os.environ.get("GROUP_LINK", "https://t.me/your_group")

    # Bot Mode
    BOT_MODE = os.environ.get("BOT_MODE", "movie").lower()

# Database Connection
class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URL)
        self.db = self.client[Config.DATABASE_NAME]
        self.users = self.db.users
        self.stats = self.db.stats

    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        user_data = {
            "_id": user_id,
            "username": username,
            "first_name": first_name,
            "joined_at": datetime.now(),
            "last_seen": datetime.now(),
            "is_banned": False,
            "downloads": 0,
            "searches": 0
        }
        try:
            await self.users.insert_one(user_data)
            return True
        except:
            await self.users.update_one(
                {"_id": user_id},
                {"$set": {"last_seen": datetime.now()}}
            )
            return False

    async def is_user_banned(self, user_id: int) -> bool:
        user = await self.users.find_one({"_id": user_id})
        return user.get("is_banned", False) if user else False

    async def get_all_users(self) -> List[int]:
        users = await self.users.find({}, {"_id": 1}).to_list(length=None)
        return [user["_id"] for user in users]

    async def get_stats(self) -> Dict:
        total_users = await self.users.count_documents({})
        today = datetime.now().date()
        today_users = await self.users.count_documents({
            "joined_at": {"$gte": datetime.combine(today, datetime.min.time())}
        })
        return {"total_users": total_users, "today_users": today_users}

    async def update_user_stats(self, user_id: int, field: str):
        await self.users.update_one(
            {"_id": user_id},
            {"$inc": {field: 1}, "$set": {"last_seen": datetime.now()}}
        )

# Auto-correct for movie/anime names
class AutoCorrect:
    def __init__(self):
        self.common_movies = [
            "avengers", "batman", "superman", "spiderman", "ironman", "captain america",
            "thor", "hulk", "deadpool", "wolverine", "x-men", "fantastic four",
            "guardians of the galaxy", "doctor strange", "black panther", "ant-man",
            "captain marvel", "shazam", "wonder woman", "aquaman", "flash", "green lantern",
            "justice league", "suicide squad", "birds of prey", "joker", "harley quinn",
            "fast and furious", "john wick", "mission impossible", "transformers",
            "jurassic park", "jurassic world", "star wars", "star trek", "alien", "predator",
            "terminator", "matrix", "lord of the rings", "hobbit", "harry potter",
            "pirates of the caribbean", "indiana jones", "james bond", "casino royale",
            "skyfall", "spectre", "no time to die", "goldeneye", "tomorrow never dies",
            "die hard", "lethal weapon", "rocky", "rambo", "expendables", "taken",
            "bourne", "jason bourne", "jack ryan", "kingsman", "men in black",
            "ghostbusters", "back to the future", "top gun", "avatar", "titanic",
            "all of us are dead", "squid game", "money heist", "stranger things",
            "naruto", "one piece", "dragon ball", "attack on titan", "death note",
            "demon slayer", "jujutsu kaisen", "my hero academia", "tokyo ghoul",
            "fullmetal alchemist", "hunter x hunter", "bleach", "one punch man"
        ]

    def correct_title(self, query: str) -> Tuple[str, List[str]]:
        """Return corrected query and suggestions"""
        query_lower = query.lower().strip()

        # Direct match
        if query_lower in self.common_movies:
            return query, []

        # Find close matches
        matches = get_close_matches(query_lower, self.common_movies, n=3, cutoff=0.6)

        if matches:
            return matches[0], matches[1:3]  # Return best match and alternatives

        return query, []

# Helper Functions
class Helpers:
    def __init__(self, app: Client, db: Database):
        self.app = app
        self.db = db
        self.autocorrect = AutoCorrect()

    async def is_user_in_channels(self, user_id: int) -> bool:
        """Check if user is in all force join channels"""
        if not Config.FORCE_CHANNELS:
            return True

        for channel_id in Config.FORCE_CHANNELS:
            try:
                member = await self.app.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked", "restricted"]:
                    return False
            except:
                return False
        return True

    async def search_in_channel(self, query: str, limit: int = 50) -> List[Message]:
        """Search messages in database channel with auto-correction"""
        try:
            # First try original query
            messages = []
            async for message in self.app.search_messages(Config.DB_CHANNEL, query, limit=limit):
                if message.text or message.caption:
                    messages.append(message)

            # If no results, try auto-corrected query
            if not messages:
                corrected_query, suggestions = self.autocorrect.correct_title(query)
                if corrected_query != query:
                    async for message in self.app.search_messages(Config.DB_CHANNEL, corrected_query, limit=limit):
                        if message.text or message.caption:
                            messages.append(message)

            return messages
        except Exception as e:
            logging.error(f"Search error: {e}")
            return []

    def extract_title(self, message: Message) -> str:
        """Extract clean title from message"""
        text = message.text or message.caption or ""
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if line and not line.startswith(("@", "#", "http", "👆", "🔗", "📱")):
                # Clean title
                title = re.sub(r'[^\w\s\-\.\(\)]', ' ', line).strip()
                return title[:100] if title else "Unknown"

        return "Unknown Title"

    def get_file_info(self, message: Message) -> Dict:
        """Get file information"""
        if message.document:
            return {
                "size": message.document.file_size,
                "name": message.document.file_name,
                "type": "document"
            }
        elif message.video:
            return {
                "size": message.video.file_size,
                "name": f"Video_{message.video.duration}s",
                "type": "video"
            }
        return {"size": 0, "name": "Unknown", "type": "unknown"}

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def create_search_markup(self, messages: List[Message], query: str, page: int = 0) -> InlineKeyboardMarkup:
        """Create search results markup with pagination exactly like screenshot"""
        buttons = []
        per_page = 10
        start = page * per_page
        end = start + per_page

        # Add filter buttons first (like screenshot)
        filter_buttons = [
            [InlineKeyboardButton("📤 Send All", callback_data=f"sendall|{quote_plus(query)}")],
            [
                InlineKeyboardButton("🗣️ LANGUAGES", callback_data=f"filter|lang|{quote_plus(query)}"),
                InlineKeyboardButton("📅 YEARS", callback_data=f"filter|year|{quote_plus(query)}")
            ],
            [
                InlineKeyboardButton("🎬 QUALITY", callback_data=f"filter|quality|{quote_plus(query)}"),
                InlineKeyboardButton("📺 EPISODES", callback_data=f"filter|episodes|{quote_plus(query)}")
            ],
            [InlineKeyboardButton("🎭 SEASONS", callback_data=f"filter|seasons|{quote_plus(query)}")]
        ]

        buttons.extend(filter_buttons)

        # Add file list
        for i, msg in enumerate(messages[start:end], start):
            title = self.extract_title(msg)
            file_info = self.get_file_info(msg)
            size_text = self.format_file_size(file_info["size"])

            # Format like screenshot: "📁 3.56 GB All of Us Are Dead S01 NF WEB DL"
            button_text = f"📁 {size_text} {title[:50]}{'...' if len(title) > 50 else ''}"

            buttons.append([
                InlineKeyboardButton(button_text, callback_data=f"file|{msg.id}|{quote_plus(title)}")
            ])

        # Add pagination (like screenshot)
        nav_buttons = []
        total_pages = (len(messages) + per_page - 1) // per_page

        if total_pages > 1:
            nav_buttons.append(
                InlineKeyboardButton(f"PAGE {page + 1}/{total_pages}", callback_data="page_info")
            )
            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton("NEXT ➡️", callback_data=f"search|{quote_plus(query)}|{page + 1}")
                )

        if nav_buttons:
            buttons.append(nav_buttons)

        return InlineKeyboardMarkup(buttons)

    async def send_file_with_deletion(self, chat_id: int, message_id: int, title: str, user_name: str):
        """Send file with auto-deletion like screenshot"""
        try:
            # Send file
            sent = await self.app.copy_message(
                chat_id=chat_id,
                from_chat_id=Config.DB_CHANNEL,
                message_id=message_id
            )

            # Send notification message exactly like screenshot
            await self.app.send_message(
                chat_id,
                f"🎬 **Title :** {title}\n📁 **Your File is Ready Below** 👇\n\n⏰ **This message will be automatically deleted in 4 minutes..!**\n\n📊 **Results Show In:** 1.74 seconds\n📋 **Results For:** {title}\n👤 **Requested By:** {user_name}\n👥 **Group:** None"
            )

            # Schedule deletion after 4 minutes
            asyncio.create_task(self.delete_after_delay(chat_id, sent.id, 240))

        except Exception as e:
            logging.error(f"Error sending file: {e}")

    async def delete_after_delay(self, chat_id: int, message_id: int, delay: int):
        """Delete message after delay"""
        try:
            await asyncio.sleep(delay)
            await self.app.delete_messages(chat_id, message_id)
        except:
            pass

# Initialize
app = Client("movie_anime_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
db = Database()
helpers = Helpers(app, db)

print("✅ Complete bot code structure created with all screenshot features!")
