"""
Private Telegram bot notifications for VCP screening and breakout alerts.
"""

import requests
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class TelegramMessage:
    """Telegram message configuration."""
    text: str
    parse_mode: str = "Markdown"
    disable_web_page_preview: bool = True


class TelegramBot:
    """Private Telegram bot for VCP screening notifications."""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
            logger.info("Telegram bot initialized successfully")

    def _send_message(self, message: TelegramMessage) -> bool:
        """
        Send message to Telegram chat.

        Args:
            message: TelegramMessage object

        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            logger.warning("Telegram bot not enabled - message not sent")
            return False

        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': message.text,
            'parse_mode': message.parse_mode,
            'disable_web_page_preview': message.disable_web_page_preview
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.debug("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_daily_screening_report(self, summary: Dict, top_matches: List[Dict]) -> bool:
        """
        Send daily VCP screening report.

        Args:
            summary: Screening summary statistics
            top_matches: List of top VCP matches

        Returns:
            True if message sent successfully
        """
        # Create header with emoji based on results
        if summary['vcp_patterns_detected'] == 0:
            header = "📊 *Daily VCP Screening Report*"
            emoji = "😴"
        elif summary['high_confidence_matches'] > 0:
            header = "🎯 *Daily VCP Screening Report*"
            emoji = "🔥"
        else:
            header = "📈 *Daily VCP Screening Report*"
            emoji = "⚡"

        # Build message text
        message_text = f"""{header}
📅 *Date:* {summary['scan_date'].split()[0]}

{emoji} *SUMMARY*
• Symbols Scanned: `{summary['total_symbols_scanned']}`
• VCP Patterns Found: `{summary['vcp_patterns_detected']}`
• High Confidence: `{summary['high_confidence_matches']}`
• Medium Confidence: `{summary['medium_confidence_matches']}`
• Breakouts Detected: `{summary['breakouts_detected']}`
• Detection Rate: `{summary['vcp_detection_rate']:.1f}%`
• Execution Time: `{summary['execution_time_seconds']:.0f}s`

"""

        # Add top matches if any
        if top_matches:
            message_text += "🎯 *TOP VCP MATCHES*\n"

            for i, match in enumerate(top_matches[:8], 1):  # Top 8 matches
                # Create confidence stars
                confidence_stars = "⭐" * min(3, int(match['confidence'] * 3))

                # Breakout indicator
                breakout_emoji = "🚀" if match.get('breakout_detected', False) else "⏳"

                # Volume trend emoji
                volume_emoji = {
                    'decreasing': '📉',
                    'stable': '➡️',
                    'increasing': '📈'
                }.get(match.get('volume_trend', 'stable'), '➡️')

                message_text += f"`{i:2d}.` {breakout_emoji} *{match['symbol']}* {confidence_stars}\n"
                message_text += f"     Confidence: `{match['confidence']:.2f}` | Contractions: `{match['contractions_count']}` | Base: `{match['base_length_days']}d` {volume_emoji}\n\n"

        else:
            message_text += "😴 *No VCP patterns detected today*\n"
            message_text += "The market is in a consolidation phase. VCP opportunities may emerge in the coming days.\n\n"

        # Add footer
        message_text += f"""📊 *PATTERN ANALYSIS*
• Volume Trends: """

        # Volume trend breakdown
        for trend, count in summary.get('volume_trend_distribution', {}).items():
            trend_emoji = {
                'decreasing': '📉',
                'stable': '➡️',
                'increasing': '📈',
                'insufficient_data': '❓'
            }.get(trend, '❓')
            message_text += f"{trend_emoji}{count} "

        message_text += f"""

🤖 *Generated by VCP Screening Bot*
Next scan: Tomorrow 7:00 PM ET"""

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_breakout_alert(self, alert) -> bool:
        """
        Send real-time breakout alert.

        Args:
            alert: BreakoutAlert object from Finnhub monitor

        Returns:
            True if message sent successfully
        """
        # Choose emoji based on confidence
        confidence_emoji = {
            'high': '🚀🔥',
            'medium': '🚀',
            'low': '⚡'
        }.get(alert.confidence, '⚡')

        # Format volume ratio
        volume_text = f"{alert.volume_ratio:.1f}x avg" if alert.volume_ratio > 0 else "N/A"

        message_text = f"""{confidence_emoji} *VCP BREAKOUT ALERT*

📈 *{alert.symbol}* breaking out NOW!

💰 *Price:* `${alert.current_price:.2f}`
🎯 *Resistance:* `${alert.resistance_level:.2f}`
📊 *Breakout:* `+{alert.breakout_percentage:.1f}%`
📈 *Volume:* `{volume_text}`
⭐ *Confidence:* `{alert.confidence.upper()}`

🕐 *Time:* {alert.timestamp.strftime('%H:%M:%S ET')}

🎯 Monitor for volume confirmation and continuation above resistance level.

⚠️ *Risk Management:* Consider stop-loss below resistance at `${alert.resistance_level * 0.98:.2f}`"""

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_monitoring_update(self, candidates_added: List[str], candidates_removed: List[str]) -> bool:
        """
        Send update about VCP monitoring changes.

        Args:
            candidates_added: List of newly added VCP candidates
            candidates_removed: List of removed VCP candidates

        Returns:
            True if message sent successfully
        """
        if not candidates_added and not candidates_removed:
            return True  # No changes to report

        message_text = "🔄 *VCP Monitoring Update*\n\n"

        if candidates_added:
            message_text += f"➕ *Added to monitoring:*\n"
            for symbol in candidates_added:
                message_text += f"• `{symbol}`\n"
            message_text += "\n"

        if candidates_removed:
            message_text += f"➖ *Removed from monitoring:*\n"
            for symbol in candidates_removed:
                message_text += f"• `{symbol}`\n"
            message_text += "\n"

        message_text += f"🎯 Real-time breakout monitoring active during market hours."

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_error_alert(self, error_type: str, error_message: str) -> bool:
        """
        Send error alert for system issues.

        Args:
            error_type: Type of error (e.g., "Data Fetching", "API Limit")
            error_message: Detailed error message

        Returns:
            True if message sent successfully
        """
        message_text = f"""🚨 *VCP System Alert*

❌ *Error Type:* {error_type}
🔍 *Details:* {error_message}
🕐 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

The system will attempt to recover automatically. If issues persist, manual intervention may be required."""

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_system_status(self, status: Dict) -> bool:
        """
        Send system status update.

        Args:
            status: System status dictionary

        Returns:
            True if message sent successfully
        """
        status_emoji = "✅" if status.get('healthy', True) else "⚠️"

        message_text = f"""{status_emoji} *VCP System Status*

📊 *Screening:* {"Active" if status.get('screening_active', True) else "Inactive"}
🔍 *Monitoring:* {status.get('monitored_symbols', 0)} symbols
📡 *Data Sources:* {"Operational" if status.get('data_sources_ok', True) else "Degraded"}
🤖 *Last Scan:* {status.get('last_scan', 'N/A')}

{status.get('additional_info', '')}"""

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_test_message(self) -> bool:
        """
        Send test message to verify bot configuration.

        Returns:
            True if message sent successfully
        """
        message_text = f"""🧪 *VCP Bot Test Message*

✅ Telegram bot is configured correctly!
🤖 Bot Token: Active
💬 Chat ID: Connected
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}

Your private VCP screening notifications are ready to go! 🚀"""

        message = TelegramMessage(text=message_text)
        return self._send_message(message)

    def send_message(self, text: str) -> bool:
        """
        Send generic text message to Telegram chat.

        Args:
            text: Message text to send

        Returns:
            True if message sent successfully
        """
        message = TelegramMessage(text=text)
        return self._send_message(message)

    def get_bot_info(self) -> Optional[Dict]:
        """
        Get information about the bot.

        Returns:
            Dictionary with bot information
        """
        if not self.enabled:
            return None

        url = f"{self.base_url}/getMe"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                return result.get('result')

        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")

        return None

    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate Telegram bot configuration.

        Returns:
            Dictionary with validation results
        """
        validation = {
            'bot_token_provided': bool(self.bot_token),
            'chat_id_provided': bool(self.chat_id),
            'bot_accessible': False,
            'chat_accessible': False
        }

        if validation['bot_token_provided']:
            bot_info = self.get_bot_info()
            validation['bot_accessible'] = bot_info is not None

        if validation['chat_id_provided'] and validation['bot_accessible']:
            # Try sending a test message to validate chat access
            test_success = self.send_test_message()
            validation['chat_accessible'] = test_success

        return validation


if __name__ == "__main__":
    # Test the Telegram bot
    logging.basicConfig(level=logging.INFO)

    bot = TelegramBot()

    if bot.enabled:
        print("Testing Telegram bot configuration...")

        # Validate configuration
        validation = bot.validate_configuration()
        print(f"Validation results: {validation}")

        # Get bot info
        bot_info = bot.get_bot_info()
        if bot_info:
            print(f"Bot info: {bot_info['first_name']} (@{bot_info.get('username', 'N/A')})")

        # Send test message
        if validation['chat_accessible']:
            print("✅ Telegram bot is working correctly!")
        else:
            print("❌ Telegram bot configuration issue")

        # Test daily report with sample data
        sample_summary = {
            'scan_date': '2024-01-15 19:00:00',
            'total_symbols_scanned': 503,
            'vcp_patterns_detected': 3,
            'high_confidence_matches': 1,
            'medium_confidence_matches': 2,
            'breakouts_detected': 1,
            'vcp_detection_rate': 0.6,
            'execution_time_seconds': 145,
            'volume_trend_distribution': {
                'decreasing': 2,
                'stable': 1
            }
        }

        sample_matches = [
            {
                'symbol': 'AAPL',
                'confidence': 0.85,
                'contractions_count': 3,
                'base_length_days': 42,
                'volume_trend': 'decreasing',
                'breakout_detected': True
            },
            {
                'symbol': 'MSFT',
                'confidence': 0.72,
                'contractions_count': 2,
                'base_length_days': 28,
                'volume_trend': 'stable',
                'breakout_detected': False
            }
        ]

        print("\nSending test daily report...")
        success = bot.send_daily_screening_report(sample_summary, sample_matches)
        print(f"Daily report sent: {success}")

    else:
        print("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")