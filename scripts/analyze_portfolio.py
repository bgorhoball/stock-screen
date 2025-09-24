#!/usr/bin/env python3
"""
Portfolio analysis script for paper trading workflow.
Analyzes portfolio state and prints summary statistics.
"""

import json
import sys
from datetime import datetime

try:
    with open('paper_portfolio.json', 'r') as f:
        portfolio_data = json.load(f)

    print(f'💰 Cash: ${portfolio_data.get("cash", 0):,.0f}')
    print(f'📈 Positions: {len(portfolio_data.get("positions", []))}')
    print(f'📊 Trades: {len(portfolio_data.get("closed_trades", []))}')

    # Calculate simple metrics
    if portfolio_data.get('closed_trades'):
        trades = portfolio_data['closed_trades']
        profitable_trades = [t for t in trades if t.get('pnl_dollars', 0) > 0]
        win_rate = len(profitable_trades) / len(trades) * 100

        total_pnl = sum(t.get('pnl_dollars', 0) for t in trades)
        print(f'🎯 Win Rate: {win_rate:.1f}%')
        print(f'💵 Total P&L: ${total_pnl:,.0f}')

    # Show open positions
    if portfolio_data.get('positions'):
        print('\n📋 Open Positions:')
        for pos in portfolio_data['positions']:
            symbol = pos.get('symbol', 'Unknown')
            shares = pos.get('shares', 0)
            entry_price = pos.get('entry_price', 0)
            print(f'  • {symbol}: {shares} shares @ ${entry_price:.2f}')

except Exception as e:
    print(f'Error analyzing portfolio: {e}')
    sys.exit(1)