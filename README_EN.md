# Discord Statistics Bot

Advanced statistics and leveling system bot for your Discord server.

## Features

- 📊 Detailed server statistics
- 🎤 Voice channel tracking
- 💬 Message statistics
- ⭐ Leveling system
- 📈 Graphical reports
- 😀 Emoji usage analysis
- 👥 Role tracking system

## Installation

1. Install Python 3.8 or higher
2. Clone or download the repository
3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Configure the `.env` file:
   - Create a bot on Discord Developer Portal
   - Paste your bot token into the `DISCORD_TOKEN=` field in the `.env` file
   - Optionally change the `BOT_PREFIX=` to modify the command prefix (default: !)

5. Run the bot:
```bash
python main.py
```

## Bot Commands

### 📊 General Statistics
- `!istatistik [daily/weekly/monthly]` - Server statistics
- `!kullanıcı [@user]` - User statistics
- `!kanal [#channel] [daily/weekly/monthly]` - Detailed channel statistics

### 🏆 Ranking Commands
**Voice Rankings:**
- `!g-s` - Daily voice ranking
- `!h-s` - Weekly voice ranking
- `!a-s` - Monthly voice ranking

**Message Rankings:**
- `!g-m` - Daily message ranking
- `!h-m` - Weekly message ranking
- `!a-m` - Monthly message ranking

### ⭐ Level System
- `!seviye [@user]` - Level information
- `!liderlik` - Level leaderboard

### 🎯 Other Features
- `!grafik [days]` - Activity graph (max 30 days)
- `!emojiler` - Emoji usage statistics

## Bot Permissions

The bot requires the following permissions to function properly:

- View Messages
- View Message History
- Send Messages
- Upload Files
- View Members
- View Server Statistics
- Connect to Voice Channels
- Manage Roles (optional, for role tracking)

## Troubleshooting

1. Bot is not coming online:
   - Check the token in the `.env` file
   - Make sure the bot is active in Discord Developer Portal

2. Commands are not working:
   - Verify that the bot has the necessary permissions
   - Make sure you're using the correct command prefix

3. Database errors:
   - Ensure the `discord_stats.db` file has write permissions
   - If needed, delete the file and restart the bot (this will reset the data)

## Support

For any issues or suggestions, please open an issue on GitHub. 