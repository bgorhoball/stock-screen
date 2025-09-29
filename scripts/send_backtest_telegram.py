#!/usr/bin/env python3
"""
Telegram notification script for weekly VCP strategy backtest.
Sends backtest summary via Telegram bot.
"""

import sys
import os
sys.path.append('src')

from telegram_bot import TelegramBot
from datetime import datetime
import glob

def main():
    bot = TelegramBot()
    if not bot.enabled:
        print('Telegram bot not configured')
        return 0

    # Create backtest summary message
    message = '📊 Weekly VCP Strategy Backtest\n'
    message += f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n\n'

    # Check for results
    html_reports = glob.glob('backtest_reports/*.html')

    if html_reports:
        message += f'✅ Backtest completed successfully\n'
        message += f'📄 Generated {len(html_reports)} reports\n\n'

        # Try to extract basic metrics from log
        try:
            with open('backtest.log', 'r') as f:
                log_content = f.read()

            # Look for key metrics in log
            lines = log_content.split('\n')
            metrics_found = False

            for line in lines:
                if 'Total Return:' in line:
                    message += f'📈 {line.strip()}\n'
                    metrics_found = True
                elif 'Win Rate:' in line:
                    message += f'🎯 {line.strip()}\n'
                    metrics_found = True
                elif 'Sharpe Ratio:' in line:
                    message += f'📊 {line.strip()}\n'
                    metrics_found = True

            if not metrics_found:
                message += '📋 Detailed metrics available in reports\n'

        except Exception as e:
            message += f'⚠️ Could not extract metrics: {e}\n'
    else:
        message += '❌ Backtest failed - no reports generated\n'

    message += '\n🔗 Check GitHub Actions for detailed results'

    try:
        success = bot.send_message(message)
        print(f'Telegram notification sent: {success}')
        return 0 if success else 1
    except Exception as e:
        print(f'Error sending Telegram notification: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())