"""
VCP Trading Strategy Backtesting Engine
Historical simulation with realistic transaction costs and market conditions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from .trading_strategy import VCPTradingStrategy, TradeSignal
from .portfolio_manager import PortfolioManager, ClosedTrade
from .vcp_detector import VCPDetector
from .data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

@dataclass
class BacktestResults:
    """Comprehensive backtesting results."""
    # Performance Metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float

    # Trade Statistics
    num_trades: int
    win_rate: float
    avg_gain: float
    avg_loss: float
    profit_factor: float
    avg_holding_days: float

    # Comparison to Benchmark
    benchmark_return: float
    alpha: float
    beta: float

    # Portfolio Summary
    final_value: float
    total_fees: float
    portfolio_history: List[Dict]
    trade_history: List[ClosedTrade]

    # Strategy Details
    backtest_period: str
    symbols_tested: int
    vcp_patterns_found: int

class VCPBacktester:
    """Backtesting engine for VCP trading strategy."""

    def __init__(self, strategy_config: Dict = None, portfolio_config: Dict = None):
        """
        Initialize backtester.

        Args:
            strategy_config: VCP strategy configuration
            portfolio_config: Portfolio management configuration
        """
        self.strategy = VCPTradingStrategy(strategy_config)
        self.vcp_detector = VCPDetector()
        self.data_fetcher = DataFetcher()
        self.portfolio_config = portfolio_config or {}

    def run_backtest(self, symbols: List[str], start_date: datetime,
                    end_date: datetime, initial_capital: float = 100000) -> BacktestResults:
        """
        Run comprehensive backtest on historical data.

        Args:
            symbols: List of stock symbols to test
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital

        Returns:
            BacktestResults object
        """
        logger.info(f"Starting backtest: {len(symbols)} symbols, "
                   f"{start_date.date()} to {end_date.date()}")

        # Initialize portfolio
        portfolio = PortfolioManager(initial_capital, self.portfolio_config)

        # Storage for results
        daily_values = []
        vcp_patterns_found = 0
        benchmark_data = self._get_benchmark_data(start_date, end_date)

        # Get all historical data first
        logger.info("Fetching historical data...")
        historical_data = self._fetch_historical_data(symbols, start_date, end_date)
        logger.info(f"Fetched data for {len(historical_data)} symbols")

        # Run day-by-day simulation
        current_date = start_date
        trading_days = pd.bdate_range(start_date, end_date)

        for i, trading_day in enumerate(trading_days):
            # Update progress
            if i % 50 == 0:
                progress = i / len(trading_days) * 100
                logger.info(f"Backtest progress: {progress:.1f}% ({trading_day.date()})")

            # Check for exits first
            self._process_exits(portfolio, historical_data, trading_day)

            # Look for new entry signals
            self._process_entries(portfolio, historical_data, trading_day)

            # Update portfolio values
            current_prices = self._get_current_prices(historical_data, trading_day)
            portfolio.update_positions(current_prices)
            daily_value = portfolio.get_portfolio_value(current_prices)

            # Record daily portfolio value
            daily_values.append({
                'date': trading_day,
                'portfolio_value': daily_value,
                'cash': portfolio.cash,
                'num_positions': len(portfolio.positions)
            })

        # Calculate final results
        logger.info("Calculating backtest results...")

        # Count total VCP patterns found during backtest
        vcp_patterns_found = self._count_vcp_patterns(historical_data, start_date, end_date)

        results = self._calculate_results(
            portfolio, daily_values, benchmark_data,
            start_date, end_date, len(symbols), vcp_patterns_found
        )

        logger.info(f"Backtest completed: {results.num_trades} trades, "
                   f"{results.total_return:.1%} return, {results.win_rate:.1%} win rate")

        return results

    def _fetch_historical_data(self, symbols: List[str],
                              start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for all symbols."""
        historical_data = {}
        weeks_needed = int((end_date - start_date).days / 7) + 12  # Extra buffer for analysis

        for symbol in symbols:
            try:
                data = self.data_fetcher.fetch_stock_data(symbol, weeks=weeks_needed)
                if data is not None and len(data) > 100:  # Minimum data requirement
                    # Filter to backtest period
                    mask = (data.index >= start_date) & (data.index <= end_date)
                    filtered_data = data[mask]

                    if len(filtered_data) > 50:  # Minimum trading days
                        historical_data[symbol] = data  # Keep full data for VCP analysis
                    else:
                        logger.warning(f"Insufficient data for {symbol} in backtest period")
                else:
                    logger.warning(f"Could not fetch adequate data for {symbol}")
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")

        return historical_data

    def _process_entries(self, portfolio: PortfolioManager,
                        historical_data: Dict[str, pd.DataFrame],
                        current_date: datetime) -> None:
        """Process potential entry signals for current date."""
        if len(portfolio.positions) >= self.strategy.config['max_positions']:
            return

        for symbol, data in historical_data.items():
            # Skip if already have position
            if symbol in portfolio.positions:
                continue

            # Get data up to current date for VCP analysis
            analysis_data = data[data.index <= current_date]
            if len(analysis_data) < 84:  # Need ~12 weeks minimum
                continue

            try:
                # Run VCP detection
                vcp_result = self.vcp_detector.detect_vcp(analysis_data, symbol)

                if vcp_result.detected:
                    # Check if breakout happened on or just before current date
                    if (vcp_result.breakout_date and
                        abs((current_date - vcp_result.breakout_date).days) <= 2):

                        # Generate trading signal
                        signal = self.strategy.analyze_vcp_signal(
                            vcp_result, symbol, analysis_data
                        )

                        if signal:
                            # Calculate position size
                            portfolio_value = portfolio.get_portfolio_value()
                            shares = self.strategy.calculate_position_size(signal, portfolio_value)

                            if shares > 0:
                                # Open position
                                position = portfolio.open_position(signal, shares)
                                if position:
                                    logger.debug(f"{current_date.date()}: Opened {symbol} "
                                               f"at ${signal.price:.2f}")

            except Exception as e:
                logger.error(f"Error processing entry for {symbol}: {e}")

    def _process_exits(self, portfolio: PortfolioManager,
                      historical_data: Dict[str, pd.DataFrame],
                      current_date: datetime) -> None:
        """Process potential exit signals for current date."""
        symbols_to_exit = []

        for symbol, position in portfolio.positions.items():
            if symbol not in historical_data:
                continue

            try:
                # Get current price
                data = historical_data[symbol]
                current_data = data[data.index <= current_date]

                if current_data.empty:
                    continue

                current_price = current_data['close'].iloc[-1]

                # Check for exit signal
                exit_signal = self.strategy.should_exit_position(position, current_price)

                if exit_signal:
                    symbols_to_exit.append((symbol, exit_signal))

            except Exception as e:
                logger.error(f"Error processing exit for {symbol}: {e}")

        # Execute exits
        for symbol, exit_signal in symbols_to_exit:
            closed_trade = portfolio.close_position(symbol, exit_signal)
            if closed_trade:
                logger.debug(f"{current_date.date()}: Closed {symbol} "
                           f"for {closed_trade.pnl_percent:.1%}")

    def _get_current_prices(self, historical_data: Dict[str, pd.DataFrame],
                           current_date: datetime) -> Dict[str, float]:
        """Get current prices for all symbols."""
        current_prices = {}

        for symbol, data in historical_data.items():
            try:
                current_data = data[data.index <= current_date]
                if not current_data.empty:
                    current_prices[symbol] = current_data['close'].iloc[-1]
            except Exception as e:
                logger.error(f"Error getting current price for {symbol}: {e}")

        return current_prices

    def _get_benchmark_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get benchmark (SPY) data for comparison."""
        try:
            weeks_needed = int((end_date - start_date).days / 7) + 4
            spy_data = self.data_fetcher.fetch_stock_data('SPY', weeks=weeks_needed)

            if spy_data is not None:
                mask = (spy_data.index >= start_date) & (spy_data.index <= end_date)
                return spy_data[mask]

        except Exception as e:
            logger.error(f"Error fetching benchmark data: {e}")

        # Return empty DataFrame if failed
        return pd.DataFrame()

    def _count_vcp_patterns(self, historical_data: Dict[str, pd.DataFrame],
                           start_date: datetime, end_date: datetime) -> int:
        """Count total VCP patterns found during backtest period."""
        total_patterns = 0

        for symbol, data in historical_data.items():
            try:
                analysis_data = data[data.index <= end_date]
                if len(analysis_data) >= 84:
                    vcp_result = self.vcp_detector.detect_vcp(analysis_data, symbol)
                    if vcp_result.detected:
                        total_patterns += 1
            except Exception:
                continue

        return total_patterns

    def _calculate_results(self, portfolio: PortfolioManager, daily_values: List[Dict],
                          benchmark_data: pd.DataFrame, start_date: datetime,
                          end_date: datetime, symbols_tested: int,
                          vcp_patterns_found: int) -> BacktestResults:
        """Calculate comprehensive backtest results."""

        # Basic performance metrics
        initial_value = portfolio.initial_capital
        final_value = daily_values[-1]['portfolio_value'] if daily_values else initial_value
        total_return = (final_value - initial_value) / initial_value

        # Calculate daily returns
        portfolio_values = [d['portfolio_value'] for d in daily_values]
        daily_returns = np.diff(portfolio_values) / portfolio_values[:-1]

        # Annualized metrics
        days = len(daily_values)
        years = days / 252.0  # Trading days per year
        annual_return = (final_value / initial_value) ** (1/years) - 1 if years > 0 else 0
        volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0

        # Risk metrics
        max_drawdown = self._calculate_max_drawdown(portfolio_values)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

        # Trade statistics
        trades = portfolio.closed_trades
        winning_trades = [t for t in trades if t.pnl_dollars > 0]
        losing_trades = [t for t in trades if t.pnl_dollars <= 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_gain = np.mean([t.pnl_percent for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_percent for t in losing_trades]) if losing_trades else 0
        avg_holding_days = np.mean([t.holding_days for t in trades]) if trades else 0

        # Profit factor
        gross_profit = sum(t.pnl_dollars for t in winning_trades)
        gross_loss = abs(sum(t.pnl_dollars for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        # Benchmark comparison
        benchmark_return = 0
        alpha = 0
        beta = 0

        if not benchmark_data.empty:
            benchmark_start = benchmark_data['close'].iloc[0]
            benchmark_end = benchmark_data['close'].iloc[-1]
            benchmark_return = (benchmark_end - benchmark_start) / benchmark_start

            # Calculate alpha and beta
            benchmark_returns = benchmark_data['close'].pct_change().dropna()
            if len(benchmark_returns) > 0 and len(daily_returns) > 0:
                # Align returns by date
                portfolio_dates = [d['date'] for d in daily_values[1:]]  # Skip first day
                aligned_returns = self._align_returns(daily_returns, portfolio_dates, benchmark_returns)

                if len(aligned_returns[0]) > 10:  # Need enough data points
                    port_returns, bench_returns = aligned_returns
                    covariance = np.cov(port_returns, bench_returns)[0][1]
                    benchmark_variance = np.var(bench_returns)

                    if benchmark_variance > 0:
                        beta = covariance / benchmark_variance
                        alpha = annual_return - (0.02 + beta * (np.mean(bench_returns) * 252 - 0.02))

        # Total fees
        total_fees = len(trades) * 2 * portfolio.config.get('commission', 1.0)  # Entry + exit

        return BacktestResults(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            num_trades=len(trades),
            win_rate=win_rate,
            avg_gain=avg_gain,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_holding_days=avg_holding_days,
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta,
            final_value=final_value,
            total_fees=total_fees,
            portfolio_history=daily_values,
            trade_history=trades,
            backtest_period=f"{start_date.date()} to {end_date.date()}",
            symbols_tested=symbols_tested,
            vcp_patterns_found=vcp_patterns_found
        )

    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """Calculate maximum drawdown."""
        if not portfolio_values:
            return 0.0

        peak = portfolio_values[0]
        max_dd = 0.0

        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_sharpe_ratio(self, daily_returns: np.ndarray) -> float:
        """Calculate Sharpe ratio."""
        if len(daily_returns) < 30:
            return 0.0

        excess_returns = daily_returns - (0.02 / 252)  # Risk-free rate

        if np.std(excess_returns) == 0:
            return 0.0

        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)

    def _align_returns(self, portfolio_returns: np.ndarray, portfolio_dates: List[datetime],
                      benchmark_returns: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Align portfolio and benchmark returns by date."""
        aligned_port = []
        aligned_bench = []

        for i, date in enumerate(portfolio_dates):
            if date in benchmark_returns.index and i < len(portfolio_returns):
                aligned_port.append(portfolio_returns[i])
                aligned_bench.append(benchmark_returns[date])

        return np.array(aligned_port), np.array(aligned_bench)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test backtester with sample data
    backtester = VCPBacktester()

    # Test with a few symbols over a short period
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    start_date = datetime.now() - timedelta(days=365)  # 1 year ago
    end_date = datetime.now() - timedelta(days=30)     # 1 month ago

    print(f"Running test backtest: {len(test_symbols)} symbols")
    print(f"Period: {start_date.date()} to {end_date.date()}")

    results = backtester.run_backtest(test_symbols, start_date, end_date, 100000)

    print(f"\nBacktest Results:")
    print(f"Total Return: {results.total_return:.1%}")
    print(f"Annual Return: {results.annual_return:.1%}")
    print(f"Max Drawdown: {results.max_drawdown:.1%}")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"Number of Trades: {results.num_trades}")
    print(f"Win Rate: {results.win_rate:.1%}")
    print(f"VCP Patterns Found: {results.vcp_patterns_found}")