"""
VCP Trading Strategy Implementation
Based on Mark Minervini's Volatility Contraction Pattern methodology
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging
from .vcp_detector import VCPResult
from .data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    """Trading signal for VCP breakout."""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'STOP'
    price: float
    timestamp: datetime
    confidence: float
    reason: str
    volume_ratio: float = 0.0
    stop_loss: float = 0.0
    profit_target: float = 0.0

@dataclass
class Position:
    """Open trading position."""
    symbol: str
    entry_date: datetime
    entry_price: float
    shares: int
    stop_loss: float
    profit_target: float
    confidence: float
    current_price: float = 0.0
    days_held: int = 0
    unrealized_pnl: float = 0.0
    status: str = 'OPEN'  # 'OPEN', 'CLOSED'

@dataclass
class ClosedTrade:
    """Completed trade with results."""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    shares: int
    holding_days: int
    pnl_dollars: float
    pnl_percent: float
    exit_reason: str  # 'PROFIT_TARGET', 'STOP_LOSS', 'TIME_STOP'
    confidence: float

class VCPTradingStrategy:
    """VCP trading strategy with entry/exit rules and risk management."""

    def __init__(self, config: Dict = None):
        """
        Initialize trading strategy.

        Args:
            config: Strategy configuration parameters
        """
        default_config = {
            # Entry Criteria
            'min_confidence': 0.8,           # Minimum VCP confidence score
            'min_volume_ratio': 1.5,         # Breakout volume vs average
            'market_trend_window': 50,       # Days for market trend check

            # Risk Management
            'stop_loss_percent': 0.08,       # 8% stop loss
            'profit_target_percent': 0.25,   # 25% profit target
            'max_holding_days': 56,          # 8 weeks maximum hold
            'trailing_stop_trigger': 0.10,   # Start trailing at 10% gain
            'trailing_stop_percent': 0.05,   # 5% trailing stop

            # Position Sizing
            'risk_per_trade': 0.02,          # 2% portfolio risk per trade
            'max_position_size': 0.10,       # 10% max single position
            'max_positions': 15,             # Maximum concurrent positions
            'max_sector_allocation': 0.30,   # 30% max per sector

            # Market Conditions
            'bear_market_reduction': 0.5,    # Reduce size in bear market
            'high_vix_threshold': 25,        # High volatility threshold
            'earnings_blackout_days': 7,     # Days before earnings to avoid
        }

        self.config = {**default_config, **(config or {})}
        self.data_fetcher = DataFetcher()

    def analyze_vcp_signal(self, vcp_result: VCPResult, symbol: str,
                          current_data: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Analyze VCP result and generate trading signal.

        Args:
            vcp_result: VCP detection result
            symbol: Stock symbol
            current_data: Current price data

        Returns:
            TradeSignal if entry criteria met, None otherwise
        """
        if not vcp_result.detected:
            return None

        # Check confidence threshold
        if vcp_result.confidence < self.config['min_confidence']:
            logger.debug(f"{symbol}: Confidence {vcp_result.confidence:.2f} below threshold")
            return None

        # Check if breakout already occurred
        if not vcp_result.breakout_date or not vcp_result.breakout_price:
            logger.debug(f"{symbol}: No breakout detected yet")
            return None

        # Validate breakout is recent (within last 5 days)
        days_since_breakout = (datetime.now() - vcp_result.breakout_date).days
        if days_since_breakout > 5:
            logger.debug(f"{symbol}: Breakout too old ({days_since_breakout} days)")
            return None

        # Check volume confirmation
        volume_ratio = self._calculate_volume_ratio(current_data, vcp_result.breakout_date)
        if volume_ratio < self.config['min_volume_ratio']:
            logger.debug(f"{symbol}: Insufficient volume ratio {volume_ratio:.2f}")
            return None

        # Check market trend
        if not self._is_market_favorable():
            logger.debug(f"{symbol}: Unfavorable market conditions")
            return None

        # Calculate entry levels
        entry_price = vcp_result.breakout_price
        stop_loss = entry_price * (1 - self.config['stop_loss_percent'])
        profit_target = entry_price * (1 + self.config['profit_target_percent'])

        return TradeSignal(
            symbol=symbol,
            signal_type='BUY',
            price=entry_price,
            timestamp=vcp_result.breakout_date,
            confidence=vcp_result.confidence,
            reason=f"VCP breakout with {volume_ratio:.1f}x volume",
            volume_ratio=volume_ratio,
            stop_loss=stop_loss,
            profit_target=profit_target
        )

    def calculate_position_size(self, signal: TradeSignal,
                               portfolio_value: float) -> int:
        """
        Calculate position size based on risk management rules.

        Args:
            signal: Trading signal
            portfolio_value: Current portfolio value

        Returns:
            Number of shares to buy
        """
        # Risk-based position sizing
        risk_amount = portfolio_value * self.config['risk_per_trade']
        price_risk = signal.price - signal.stop_loss

        if price_risk <= 0:
            logger.warning(f"{signal.symbol}: Invalid stop loss level")
            return 0

        shares_by_risk = int(risk_amount / price_risk)

        # Maximum position size constraint
        max_position_value = portfolio_value * self.config['max_position_size']
        max_shares_by_value = int(max_position_value / signal.price)

        # Take the smaller of the two
        shares = min(shares_by_risk, max_shares_by_value)

        # Adjust for market conditions
        if not self._is_market_favorable():
            shares = int(shares * self.config['bear_market_reduction'])

        logger.info(f"{signal.symbol}: Position size {shares} shares "
                   f"(${shares * signal.price:.0f}, {price_risk:.2f} risk)")

        return max(0, shares)

    def should_exit_position(self, position: Position,
                           current_price: float) -> Optional[TradeSignal]:
        """
        Check if position should be exited.

        Args:
            position: Current position
            current_price: Current stock price

        Returns:
            Exit signal if position should be closed, None otherwise
        """
        # Update position metrics
        position.current_price = current_price
        position.days_held = (datetime.now() - position.entry_date).days
        position.unrealized_pnl = (current_price - position.entry_price) / position.entry_price

        # Check stop loss
        if current_price <= position.stop_loss:
            return TradeSignal(
                symbol=position.symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=datetime.now(),
                confidence=1.0,
                reason="Stop loss triggered"
            )

        # Check profit target
        if current_price >= position.profit_target:
            return TradeSignal(
                symbol=position.symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=datetime.now(),
                confidence=1.0,
                reason="Profit target reached"
            )

        # Check time stop
        if position.days_held >= self.config['max_holding_days']:
            return TradeSignal(
                symbol=position.symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=datetime.now(),
                confidence=0.8,
                reason="Time stop (max holding period)"
            )

        # Check trailing stop
        gain_percent = position.unrealized_pnl
        if gain_percent >= self.config['trailing_stop_trigger']:
            trailing_stop = position.entry_price * (1 + gain_percent - self.config['trailing_stop_percent'])
            if current_price <= trailing_stop:
                return TradeSignal(
                    symbol=position.symbol,
                    signal_type='SELL',
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=0.9,
                    reason=f"Trailing stop ({gain_percent:.1%} gain)"
                )

        return None

    def _calculate_volume_ratio(self, data: pd.DataFrame,
                               breakout_date: datetime) -> float:
        """Calculate volume ratio on breakout day vs average."""
        try:
            # Find breakout day data
            breakout_data = data[data.index.date == breakout_date.date()]
            if breakout_data.empty:
                return 0.0

            breakout_volume = breakout_data['volume'].iloc[0]

            # Calculate 20-day average volume (excluding breakout day)
            recent_data = data[data.index < breakout_date].tail(20)
            if len(recent_data) < 10:
                return 0.0

            avg_volume = recent_data['volume'].mean()

            return breakout_volume / avg_volume if avg_volume > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating volume ratio: {e}")
            return 0.0

    def _is_market_favorable(self) -> bool:
        """
        Check if market conditions are favorable for new positions.

        Returns:
            True if market is favorable, False otherwise
        """
        try:
            # Get SPY data for market trend analysis
            spy_data = self.data_fetcher.fetch_stock_data('SPY', weeks=12)
            if spy_data is None or len(spy_data) < self.config['market_trend_window']:
                logger.warning("Insufficient SPY data for market analysis")
                return True  # Default to favorable if can't determine

            # Check if SPY is above moving average
            current_price = spy_data['close'].iloc[-1]
            ma_window = self.config['market_trend_window']
            moving_average = spy_data['close'].tail(ma_window).mean()

            is_uptrend = current_price > moving_average

            # Calculate recent volatility (VIX proxy)
            returns = spy_data['close'].pct_change().tail(20)
            volatility = returns.std() * np.sqrt(252) * 100  # Annualized vol %
            is_low_vol = volatility < self.config['high_vix_threshold']

            logger.info(f"Market analysis: Uptrend={is_uptrend}, "
                       f"Volatility={volatility:.1f}%, Favorable={is_uptrend and is_low_vol}")

            return is_uptrend and is_low_vol

        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return True  # Default to favorable on error

    def get_strategy_stats(self) -> Dict:
        """Get current strategy statistics and settings."""
        return {
            'config': self.config,
            'market_favorable': self._is_market_favorable(),
            'last_update': datetime.now().isoformat()
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test the trading strategy
    strategy = VCPTradingStrategy()

    # Test with sample VCP result
    from .vcp_detector import VCPResult

    sample_vcp = VCPResult(
        detected=True,
        confidence=0.85,
        contractions=[],
        breakout_date=datetime.now() - timedelta(days=1),
        breakout_price=150.0,
        base_length_days=30,
        volume_trend="decreasing",
        notes=["High confidence VCP pattern"]
    )

    # Get sample data and test signal generation
    data_fetcher = DataFetcher()
    test_data = data_fetcher.fetch_stock_data('AAPL', weeks=4)

    if test_data is not None:
        signal = strategy.analyze_vcp_signal(sample_vcp, 'AAPL', test_data)
        if signal:
            print(f"Generated signal: {signal}")

            # Test position sizing
            portfolio_value = 100000
            shares = strategy.calculate_position_size(signal, portfolio_value)
            print(f"Position size: {shares} shares")
        else:
            print("No signal generated")
    else:
        print("Could not fetch test data")