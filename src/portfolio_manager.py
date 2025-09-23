"""
Portfolio Management for VCP Trading Strategy
Handles position tracking, risk management, and portfolio statistics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import logging
from .trading_strategy import TradeSignal, Position, ClosedTrade

logger = logging.getLogger(__name__)

@dataclass
class PortfolioStats:
    """Portfolio performance statistics."""
    total_value: float
    cash: float
    invested: float
    unrealized_pnl: float
    realized_pnl: float
    total_return: float
    num_positions: int
    num_trades: int
    win_rate: float
    avg_gain: float
    avg_loss: float
    max_drawdown: float
    sharpe_ratio: float
    last_updated: datetime = field(default_factory=datetime.now)

class PortfolioManager:
    """Manages trading portfolio, positions, and risk controls."""

    def __init__(self, initial_capital: float = 100000, config: Dict = None):
        """
        Initialize portfolio manager.

        Args:
            initial_capital: Starting portfolio value
            config: Portfolio management configuration
        """
        default_config = {
            'max_positions': 15,
            'max_sector_allocation': 0.30,
            'max_single_position': 0.10,
            'cash_reserve': 0.05,  # Keep 5% cash
            'rebalance_threshold': 0.15,  # Rebalance if allocation > 15% off target
            'commission': 1.0,  # Commission per trade
            'slippage': 0.001,  # 0.1% slippage
        }

        self.config = {**default_config, **(config or {})}
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[ClosedTrade] = []
        self.daily_returns: List[float] = []
        self.portfolio_history: List[Dict] = []

    def can_open_position(self, signal: TradeSignal, shares: int) -> Tuple[bool, str]:
        """
        Check if new position can be opened based on risk controls.

        Args:
            signal: Trading signal
            shares: Proposed number of shares

        Returns:
            Tuple of (can_open, reason)
        """
        # Check maximum positions
        if len(self.positions) >= self.config['max_positions']:
            return False, f"Maximum positions limit ({self.config['max_positions']})"

        # Check if already have position in this symbol
        if signal.symbol in self.positions:
            return False, f"Already have position in {signal.symbol}"

        # Check cash availability
        required_cash = shares * signal.price + self.config['commission']
        if required_cash > self.cash:
            return False, f"Insufficient cash (need ${required_cash:.0f}, have ${self.cash:.0f})"

        # Check position size limits
        position_value = shares * signal.price
        portfolio_value = self.get_portfolio_value()
        position_percent = position_value / portfolio_value

        if position_percent > self.config['max_single_position']:
            return False, f"Position too large ({position_percent:.1%} > {self.config['max_single_position']:.1%})"

        # Check cash reserve
        remaining_cash = self.cash - required_cash
        min_cash = portfolio_value * self.config['cash_reserve']
        if remaining_cash < min_cash:
            return False, f"Would violate cash reserve requirement"

        # Check sector allocation (if sector data available)
        # TODO: Implement sector checking when sector data is added

        return True, "Position approved"

    def open_position(self, signal: TradeSignal, shares: int) -> Optional[Position]:
        """
        Open a new position.

        Args:
            signal: Trading signal
            shares: Number of shares to buy

        Returns:
            Position object if successful, None otherwise
        """
        can_open, reason = self.can_open_position(signal, shares)
        if not can_open:
            logger.warning(f"Cannot open position in {signal.symbol}: {reason}")
            return None

        # Apply slippage to entry price
        entry_price = signal.price * (1 + self.config['slippage'])
        total_cost = shares * entry_price + self.config['commission']

        # Create position
        position = Position(
            symbol=signal.symbol,
            entry_date=signal.timestamp,
            entry_price=entry_price,
            shares=shares,
            stop_loss=signal.stop_loss,
            profit_target=signal.profit_target,
            confidence=signal.confidence,
            current_price=entry_price
        )

        # Update portfolio
        self.cash -= total_cost
        self.positions[signal.symbol] = position

        logger.info(f"Opened position: {shares} shares of {signal.symbol} at ${entry_price:.2f}")
        return position

    def close_position(self, symbol: str, exit_signal: TradeSignal) -> Optional[ClosedTrade]:
        """
        Close an existing position.

        Args:
            symbol: Stock symbol
            exit_signal: Exit trading signal

        Returns:
            ClosedTrade object if successful, None otherwise
        """
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return None

        position = self.positions[symbol]

        # Apply slippage to exit price
        exit_price = exit_signal.price * (1 - self.config['slippage'])
        proceeds = position.shares * exit_price - self.config['commission']

        # Calculate trade results
        holding_days = (exit_signal.timestamp - position.entry_date).days
        pnl_dollars = proceeds - (position.shares * position.entry_price + self.config['commission'])
        pnl_percent = pnl_dollars / (position.shares * position.entry_price)

        # Create closed trade record
        closed_trade = ClosedTrade(
            symbol=symbol,
            entry_date=position.entry_date,
            exit_date=exit_signal.timestamp,
            entry_price=position.entry_price,
            exit_price=exit_price,
            shares=position.shares,
            holding_days=holding_days,
            pnl_dollars=pnl_dollars,
            pnl_percent=pnl_percent,
            exit_reason=exit_signal.reason,
            confidence=position.confidence
        )

        # Update portfolio
        self.cash += proceeds
        self.closed_trades.append(closed_trade)
        del self.positions[symbol]

        logger.info(f"Closed position: {symbol} for ${pnl_dollars:.0f} "
                   f"({pnl_percent:.1%}) after {holding_days} days")
        return closed_trade

    def update_positions(self, price_data: Dict[str, float]) -> None:
        """
        Update current prices and unrealized P&L for all positions.

        Args:
            price_data: Dictionary of symbol -> current price
        """
        for symbol, position in self.positions.items():
            if symbol in price_data:
                position.current_price = price_data[symbol]
                position.days_held = (datetime.now() - position.entry_date).days
                position.unrealized_pnl = ((position.current_price - position.entry_price)
                                         / position.entry_price)

    def get_portfolio_value(self, price_data: Dict[str, float] = None) -> float:
        """
        Calculate total portfolio value.

        Args:
            price_data: Current price data (optional)

        Returns:
            Total portfolio value
        """
        if price_data:
            self.update_positions(price_data)

        invested_value = sum(
            pos.shares * pos.current_price for pos in self.positions.values()
        )
        return self.cash + invested_value

    def get_portfolio_stats(self) -> PortfolioStats:
        """
        Calculate comprehensive portfolio statistics.

        Returns:
            PortfolioStats object
        """
        # Basic metrics
        portfolio_value = self.get_portfolio_value()
        invested = sum(pos.shares * pos.current_price for pos in self.positions.values())
        unrealized_pnl = sum(pos.shares * (pos.current_price - pos.entry_price)
                           for pos in self.positions.values())
        realized_pnl = sum(trade.pnl_dollars for trade in self.closed_trades)
        total_return = (portfolio_value - self.initial_capital) / self.initial_capital

        # Trade statistics
        winning_trades = [t for t in self.closed_trades if t.pnl_dollars > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl_dollars <= 0]

        win_rate = len(winning_trades) / len(self.closed_trades) if self.closed_trades else 0
        avg_gain = np.mean([t.pnl_percent for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_percent for t in losing_trades]) if losing_trades else 0

        # Risk metrics
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio()

        return PortfolioStats(
            total_value=portfolio_value,
            cash=self.cash,
            invested=invested,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            total_return=total_return,
            num_positions=len(self.positions),
            num_trades=len(self.closed_trades),
            win_rate=win_rate,
            avg_gain=avg_gain,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio
        )

    def get_position_summary(self) -> List[Dict]:
        """
        Get summary of all open positions.

        Returns:
            List of position dictionaries
        """
        return [
            {
                'symbol': pos.symbol,
                'shares': pos.shares,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'entry_date': pos.entry_date.strftime('%Y-%m-%d'),
                'days_held': pos.days_held,
                'unrealized_pnl': pos.unrealized_pnl,
                'stop_loss': pos.stop_loss,
                'profit_target': pos.profit_target,
                'confidence': pos.confidence
            }
            for pos in self.positions.values()
        ]

    def get_trade_history(self, limit: int = None) -> List[Dict]:
        """
        Get history of closed trades.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries
        """
        trades = sorted(self.closed_trades, key=lambda t: t.exit_date, reverse=True)
        if limit:
            trades = trades[:limit]

        return [
            {
                'symbol': trade.symbol,
                'entry_date': trade.entry_date.strftime('%Y-%m-%d'),
                'exit_date': trade.exit_date.strftime('%Y-%m-%d'),
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'shares': trade.shares,
                'holding_days': trade.holding_days,
                'pnl_dollars': trade.pnl_dollars,
                'pnl_percent': trade.pnl_percent,
                'exit_reason': trade.exit_reason,
                'confidence': trade.confidence
            }
            for trade in trades
        ]

    def save_portfolio_state(self, filepath: str) -> None:
        """
        Save portfolio state to JSON file.

        Args:
            filepath: Path to save file
        """
        state = {
            'cash': self.cash,
            'initial_capital': self.initial_capital,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'entry_date': pos.entry_date.isoformat(),
                    'entry_price': pos.entry_price,
                    'shares': pos.shares,
                    'stop_loss': pos.stop_loss,
                    'profit_target': pos.profit_target,
                    'confidence': pos.confidence,
                    'current_price': pos.current_price
                }
                for pos in self.positions.values()
            ],
            'closed_trades': [
                {
                    'symbol': trade.symbol,
                    'entry_date': trade.entry_date.isoformat(),
                    'exit_date': trade.exit_date.isoformat(),
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'shares': trade.shares,
                    'holding_days': trade.holding_days,
                    'pnl_dollars': trade.pnl_dollars,
                    'pnl_percent': trade.pnl_percent,
                    'exit_reason': trade.exit_reason,
                    'confidence': trade.confidence
                }
                for trade in self.closed_trades
            ],
            'timestamp': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"Portfolio state saved to {filepath}")

    def load_portfolio_state(self, filepath: str) -> None:
        """
        Load portfolio state from JSON file.

        Args:
            filepath: Path to load file
        """
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)

            self.cash = state['cash']
            self.initial_capital = state['initial_capital']

            # Restore positions
            self.positions = {}
            for pos_data in state['positions']:
                position = Position(
                    symbol=pos_data['symbol'],
                    entry_date=datetime.fromisoformat(pos_data['entry_date']),
                    entry_price=pos_data['entry_price'],
                    shares=pos_data['shares'],
                    stop_loss=pos_data['stop_loss'],
                    profit_target=pos_data['profit_target'],
                    confidence=pos_data['confidence'],
                    current_price=pos_data['current_price']
                )
                self.positions[position.symbol] = position

            # Restore closed trades
            self.closed_trades = []
            for trade_data in state['closed_trades']:
                trade = ClosedTrade(
                    symbol=trade_data['symbol'],
                    entry_date=datetime.fromisoformat(trade_data['entry_date']),
                    exit_date=datetime.fromisoformat(trade_data['exit_date']),
                    entry_price=trade_data['entry_price'],
                    exit_price=trade_data['exit_price'],
                    shares=trade_data['shares'],
                    holding_days=trade_data['holding_days'],
                    pnl_dollars=trade_data['pnl_dollars'],
                    pnl_percent=trade_data['pnl_percent'],
                    exit_reason=trade_data['exit_reason'],
                    confidence=trade_data['confidence']
                )
                self.closed_trades.append(trade)

            logger.info(f"Portfolio state loaded from {filepath}")

        except Exception as e:
            logger.error(f"Error loading portfolio state: {e}")

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from portfolio history."""
        if not self.portfolio_history:
            return 0.0

        values = [entry['portfolio_value'] for entry in self.portfolio_history]
        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from daily returns."""
        if len(self.daily_returns) < 30:
            return 0.0

        returns = np.array(self.daily_returns)
        excess_returns = returns - 0.02/252  # Assume 2% risk-free rate

        if returns.std() == 0:
            return 0.0

        return np.sqrt(252) * excess_returns.mean() / returns.std()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test portfolio manager
    portfolio = PortfolioManager(initial_capital=100000)

    # Test with sample signal and position
    from .trading_strategy import TradeSignal
    from datetime import datetime

    sample_signal = TradeSignal(
        symbol='AAPL',
        signal_type='BUY',
        price=150.0,
        timestamp=datetime.now(),
        confidence=0.85,
        reason="VCP breakout",
        stop_loss=138.0,
        profit_target=187.5
    )

    # Test opening position
    shares = 100
    position = portfolio.open_position(sample_signal, shares)
    if position:
        print(f"Position opened: {position}")

        # Test portfolio stats
        stats = portfolio.get_portfolio_stats()
        print(f"Portfolio stats: Total value=${stats.total_value:.0f}, "
              f"Cash=${stats.cash:.0f}, Positions={stats.num_positions}")
    else:
        print("Failed to open position")