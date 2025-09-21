# Telegram Bot Setup Guide

This guide will walk you through setting up a private Telegram bot for VCP screening notifications.

## 📱 Why Telegram?

- ✅ **Free unlimited messaging** - No API costs
- ✅ **Instant notifications** - Real-time breakout alerts
- ✅ **Rich formatting** - Beautiful reports with emojis and formatting
- ✅ **Mobile + Desktop** - Get alerts anywhere
- ✅ **Private and secure** - Your notifications stay private
- ✅ **Easy setup** - No phone number required

## 🤖 Step 1: Create Your Telegram Bot

### 1.1 Start a chat with BotFather
1. Open Telegram app (mobile or desktop)
2. Search for `@BotFather` and start a chat
3. Send `/start` to begin

### 1.2 Create a new bot
1. Send `/newbot` to BotFather
2. Choose a name for your bot (e.g., "My VCP Screener")
3. Choose a username ending in 'bot' (e.g., "my_vcp_screener_bot")

### 1.3 Get your bot token
BotFather will send you a message like:
```
Congratulations! You have just created a new bot.
Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**⚠️ IMPORTANT**: Keep this token secret! It's like a password for your bot.

## 💬 Step 2: Get Your Chat ID

### 2.1 Start a chat with your bot
1. Click the link BotFather provided, or search for your bot username
2. Click **START** or send `/start` to your bot

### 2.2 Get your Chat ID
1. Send any message to your bot (e.g., "Hello")
2. Open this link in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Look for your message in the JSON response
4. Find the `"chat":{"id":` number (e.g., 123456789)

**Example response:**
```json
{
  "result": [
    {
      "update_id": 123456789,
      "message": {
        "message_id": 1,
        "from": {"id": 987654321, "first_name": "Your Name"},
        "chat": {"id": 987654321, "first_name": "Your Name", "type": "private"},
        "date": 1640995200,
        "text": "Hello"
      }
    }
  ]
}
```

Your Chat ID is the number after `"chat":{"id":` (in this example: 987654321)

## 🔐 Step 3: Add Secrets to GitHub

### 3.1 Go to your repository settings
1. Open your GitHub repository
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**

### 3.2 Add bot token
1. Click **New repository secret**
2. Name: `TELEGRAM_BOT_TOKEN`
3. Value: Your bot token from Step 1.3
4. Click **Add secret**

### 3.3 Add chat ID
1. Click **New repository secret**
2. Name: `TELEGRAM_CHAT_ID`
3. Value: Your chat ID from Step 2.2
4. Click **Add secret**

## 🧪 Step 4: Test Your Setup

### 4.1 Manual workflow test
1. Go to **Actions** tab in your repository
2. Click **Daily VCP Screening**
3. Click **Run workflow**
4. Set parameters:
   - `max_symbols`: 5
   - `dry_run`: false
5. Click **Run workflow**

### 4.2 Verify notifications
After the workflow completes (2-3 minutes), you should receive:
- 📊 Daily screening summary in Telegram
- 🔄 VCP monitoring update (if patterns found)

## 📱 What You'll Receive

### Daily Screening Reports (7 PM ET)
```
📊 Daily VCP Screening Report
📅 Date: 2024-01-15

🔥 SUMMARY
• Symbols Scanned: 503
• VCP Patterns Found: 3
• High Confidence: 1
• Medium Confidence: 2
• Breakouts Detected: 1
• Detection Rate: 0.6%
• Execution Time: 145s

🎯 TOP VCP MATCHES
 1. 🚀 AAPL ⭐⭐⭐
    Confidence: 0.85 | Contractions: 3 | Base: 42d 📉

 2. ⏳ MSFT ⭐⭐
    Confidence: 0.72 | Contractions: 2 | Base: 28d ➡️
```

### Real-Time Breakout Alerts (Market Hours)
```
🚀🔥 VCP BREAKOUT ALERT

📈 AAPL breaking out NOW!

💰 Price: $175.50
🎯 Resistance: $173.00
📊 Breakout: +1.4%
📈 Volume: 2.1x avg
⭐ Confidence: HIGH

🕐 Time: 14:23:15 ET

🎯 Monitor for volume confirmation and continuation above resistance level.

⚠️ Risk Management: Consider stop-loss below resistance at $169.54
```

### Monitoring Updates
```
🔄 VCP Monitoring Update

➕ Added to monitoring:
• AAPL
• MSFT
• GOOGL

🎯 Real-time breakout monitoring active during market hours.
```

## 🔧 Troubleshooting

### Bot not responding
- Verify bot token is correct in GitHub secrets
- Make sure you clicked START in your bot chat
- Check that bot username ends with 'bot'

### No notifications received
- Verify chat ID is correct (must be a number)
- Ensure secrets are named exactly: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Check GitHub Actions logs for error messages

### Chat ID not found
- Send a message to your bot first
- Wait a few seconds, then check getUpdates URL
- Use the numeric ID, not the username

### Testing bot configuration
You can test your bot manually:
```python
import requests

bot_token = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
message = "🧪 Test message from VCP bot!"

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": message
}

response = requests.post(url, json=payload)
print(response.json())
```

## 🎯 Next Steps

Once your Telegram bot is working:

1. **Monitor daily reports** - Review VCP patterns found each day
2. **Watch for breakout alerts** - Get instant notifications during market hours
3. **Adjust confidence thresholds** - Modify `config/config.yaml` if needed
4. **Add Finnhub API** - For enhanced real-time monitoring (optional)

## 📞 Getting Help

If you encounter issues:
1. Check your bot token and chat ID are correct
2. Verify GitHub secrets are properly named
3. Review GitHub Actions logs for detailed error messages
4. Test bot manually using the Python script above

---

**🎉 Congratulations!** Your private VCP screening bot is now ready to send you daily market insights and real-time breakout alerts!

## 📋 Quick Reference

**Required GitHub Secrets:**
- `TELEGRAM_BOT_TOKEN` - Your bot token from BotFather
- `TELEGRAM_CHAT_ID` - Your numeric chat ID

**Notification Schedule:**
- **Daily reports**: 7:00 PM ET (Monday-Friday)
- **Breakout alerts**: Real-time during market hours (9:30 AM - 4:00 PM ET)
- **System updates**: As needed

**Bot Commands:**
- Send any message to your bot to test connectivity
- Bot will only send notifications (doesn't respond to commands)