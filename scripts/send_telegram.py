#!/usr/bin/env python3
"""
Telegram notification script for paper trading workflow.
Sends daily paper trading summary via Telegram bot.
"""

import sys
import os
sys.path.append('src')

from telegram_bot import TelegramBot
import json
from datetime import datetime

def main():
    bot = TelegramBot()
    if not bot.enabled:
        print('Telegram bot not configured - skipping notification')
        return 0

    # Build summary message
    message = '📈 Daily Paper Trading Summary\n'
    message += f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M ET")}\n\n'

    # Portfolio summary
    try:
        if os.path.exists('paper_portfolio.json'):
            with open('paper_portfolio.json', 'r') as f:
                portfolio = json.load(f)

            cash = portfolio.get('cash', 0)
            positions = portfolio.get('positions', [])
            trades = portfolio.get('closed_trades', [])

            message += f'💼 Portfolio Status:\n'
            message += f'Cash: ${cash:,.0f}\n'
            message += f'Positions: {len(positions)}\n'
            message += f'Total Trades: {len(trades)}\n'

            # Calculate total portfolio value (simplified)
            invested_value = sum(p.get('shares', 0) * p.get('current_price', p.get('entry_price', 0))
                               for p in positions)
            total_value = cash + invested_value
            initial_capital = portfolio.get('initial_capital', 100000)
            total_return = (total_value - initial_capital) / initial_capital

            message += f'Total Value: ${total_value:,.0f}\n'
            message += f'Return: {total_return:.1%}\n'

            # Recent trades today
            today = datetime.now().date().isoformat()
            today_trades = [t for t in trades if t.get('exit_date', '')[:10] == today]

            if today_trades:
                message += f'\n📊 Today\'s Trades ({len(today_trades)}): \n'
                for trade in today_trades:
                    symbol = trade.get('symbol', 'Unknown')
                    pnl_pct = trade.get('pnl_percent', 0) * 100
                    pnl_emoji = '💰' if pnl_pct > 0 else '📉'
                    message += f'{pnl_emoji} {symbol}: {pnl_pct:+.1f}%\n'

            # Top positions
            if positions:
                message += f'\n📈 Current Positions:\n'
                for pos in positions[:5]:  # Show first 5
                    symbol = pos.get('symbol', 'Unknown')
                    shares = pos.get('shares', 0)
                    entry_price = pos.get('entry_price', 0)
                    current_price = pos.get('current_price', entry_price)
                    unrealized_pnl = (current_price - entry_price) / entry_price
                    message += f'• {symbol}: {shares} shares ({unrealized_pnl:+.1f}%)\n'

                if len(positions) > 5:
                    message += f'... and {len(positions) - 5} more\n'

        else:
            message += '⚠️ No portfolio data available\n'

    except Exception as e:
        message += f'❌ Error reading portfolio: {e}\n'

    # Watchlist info
    try:
        if os.path.exists('paper_watchlist.json'):
            with open('paper_watchlist.json', 'r') as f:
                watchlist = json.load(f)
            message += f'\n👀 Watchlist: {len(watchlist)} symbols\n'
    except Exception:
        pass

    message += '\n🔗 Check GitHub Actions for detailed logs'

    try:
        success = bot.send_message(message)
        print(f'Paper trading summary sent: {success}')
        return 0 if success else 1
    except Exception as e:
        print(f'Error sending summary: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())