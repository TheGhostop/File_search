# 🎬 Complete Movie/Anime Telegram Bot

## Features (Exact Match with Screenshots)
- ✅ **Force Join System** - Multi-language support
- ✅ **Group Search** - Inline search with beautiful cards
- ✅ **Pagination** - PAGE 1/53 with NEXT buttons
- ✅ **Auto File Deletion** - 4-minute timer
- ✅ **Filter Buttons** - Languages, Years, Quality, Episodes, Seasons
- ✅ **Auto-Correction** - Spell check for movie names
- ✅ **Deep Links** - t.me/botname/moviename
- ✅ **Inline Mode** - @botname query in groups
- ✅ **Owner Commands** - Stats, Broadcast, Ban
- ✅ **MongoDB Integration** - User stats only

## Quick Setup

### 1. Environment Setup
```bash
cp .env.example .env
nano .env  # Fill your details
```

### 2. Install & Run
```bash
chmod +x run.sh
./run.sh
```

### 3. Systemd Service (Production)
```bash
sudo cp movie-bot.service /etc/systemd/system/
sudo systemctl enable movie-bot
sudo systemctl start movie-bot
```

## Configuration

### Required Variables (.env)
```env
API_ID=your_api_id
API_HASH=your_api_hash  
BOT_TOKEN=your_bot_token
BOT_USERNAME=your_bot_username
DB_CHANNEL=-1001234567890
FORCE_CHANNELS=-1001111111111,-1002222222222
OWNER_ID=your_telegram_id
MONGO_URL=mongodb://localhost:27017/
BOT_MODE=movie  # or anime
```

## Bot Workflow (Exactly as Screenshots)

### 1. Group Search
- User types: "All of us dead s01"
- Bot replies with beautiful user card
- Shows paginated results with filters
- PAGE 1/53 navigation

### 2. Force Join
- Multi-language message (English + Hindi)
- Join channel buttons
- Continue to download button
- Membership verification

### 3. File Delivery
- Personal message with file
- 4-minute auto-deletion warning
- File statistics display
- User tracking

### 4. Inline Mode
- @botname query in any group
- Download File button → Deep link
- Website promotion button
- Add to group button

## Owner Commands
- `/stats` - Get user statistics
- `/broadcast` - Broadcast to all users (reply to message)

## Auto-Correction
Bot automatically corrects common misspellings:
- "avengers" → "Avengers"
- "all of us are dead" → "All of Us Are Dead"
- Plus 100+ popular movies/anime

## Features Matching Screenshots
1. **Search Results Page**: Exact filter buttons layout
2. **Force Join Message**: Multi-language support
3. **User Cards**: Beautiful formatting with emojis
4. **Pagination**: PAGE x/y format with NEXT button
5. **Auto-Deletion**: 4-minute timer with warning
6. **File Size Display**: GB/MB formatting
7. **Inline Results**: 3-button layout (Download/Site/Add)

## Single Bot for Both Movies & Anime
- Change `BOT_MODE=anime` in .env for anime bot
- Same code works for both content types
- Auto-detects and adapts interface

## Production Ready
- Error handling for all scenarios
- Rate limiting to prevent floods
- Auto-restart on crashes
- MongoDB for scalability
- Systemd integration

Just fill .env and run! 🚀
