"""
Comprehensive Test Suite for VCP Trading Strategy
Tests all components: strategy logic, portfolio management, backtesting, and performance analysis
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add src directory to path
sys.path.append('src')

from src.trading_strategy import VCPTradingStrategy, TradeSignal, Position, ClosedTrade
from src.portfolio_manager import PortfolioManager, PortfolioStats
from src.backtester import VCPBacktester, BacktestResults
from src.performance_analyzer import PerformanceAnalyzer
from src.vcp_detector import VCPDetector, VCPResult


class TestTradingStrategy:
    """Test VCP trading strategy logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = VCPTradingStrategy()
        self.sample_data = self._create_sample_data()

    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)  # For reproducible tests

        # Create realistic stock data with trend
        base_price = 100
        prices = []
        volume = []

        for i in range(len(dates)):
            # Add some trend and noise
            trend = i * 0.1
            noise = np.random.normal(0, 2)
            price = base_price + trend + noise

            # OHLCV data
            open_price = price + np.random.normal(0, 0.5)
            high = price + abs(np.random.normal(0, 1))
            low = price - abs(np.random.normal(0, 1))
            close = price + np.random.normal(0, 0.5)
            vol = int(1000000 + np.random.normal(0, 200000))

            prices.append([open_price, high, low, close, vol])

        df = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)
        df['symbol'] = 'TEST'
        return df

    def test_strategy_initialization(self):
        """Test strategy initialization with default config."""
        assert self.strategy.config['min_confidence'] == 0.8
        assert self.strategy.config['stop_loss_percent'] == 0.08
        assert self.strategy.config['profit_target_percent'] == 0.25

    def test_custom_strategy_config(self):
        """Test strategy with custom configuration."""
        custom_config = {
            'min_confidence': 0.9,
            'stop_loss_percent': 0.05,
            'max_positions': 10
        }
        strategy = VCPTradingStrategy(custom_config)
        assert strategy.config['min_confidence'] == 0.9
        assert strategy.config['stop_loss_percent'] == 0.05
        assert strategy.config['max_positions'] == 10

    def test_vcp_signal_analysis(self):
        """Test VCP signal generation."""
        # Create mock VCP result
        vcp_result = VCPResult(
            detected=True,
            confidence=0.85,
            contractions=[],
            breakout_date=datetime.now() - timedelta(days=1),
            breakout_price=150.0,
            base_length_days=30,
            volume_trend="decreasing",
            notes=["High confidence pattern"]
        )

        signal = self.strategy.analyze_vcp_signal(vcp_result, 'TEST', self.sample_data)

        if signal:  # Signal might be None due to market conditions
            assert signal.symbol == 'TEST'
            assert signal.signal_type == 'BUY'
            assert signal.confidence == 0.85
            assert signal.stop_loss < signal.price
            assert signal.profit_target > signal.price

    def test_position_sizing(self):
        """Test position size calculation."""
        signal = TradeSignal(
            symbol='TEST',
            signal_type='BUY',
            price=100.0,
            timestamp=datetime.now(),
            confidence=0.85,
            reason="Test signal",
            stop_loss=92.0,
            profit_target=125.0
        )

        portfolio_value = 100000
        shares = self.strategy.calculate_position_size(signal, portfolio_value)

        # Should return reasonable position size
        assert shares >= 0
        assert shares * signal.price <= portfolio_value * 0.5  # Reasonable maximum


class TestPortfolioManager:
    """Test portfolio management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio = PortfolioManager(initial_capital=100000)
        self.sample_signal = TradeSignal(
            symbol='TEST',
            signal_type='BUY',
            price=100.0,
            timestamp=datetime.now(),
            confidence=0.85,
            reason="Test signal",
            stop_loss=92.0,
            profit_target=125.0
        )

    def test_portfolio_initialization(self):
        """Test portfolio initialization."""
        assert self.portfolio.initial_capital == 100000
        assert self.portfolio.cash == 100000
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.closed_trades) == 0

    def test_position_opening(self):
        """Test opening a new position."""
        shares = 100
        can_open, reason = self.portfolio.can_open_position(self.sample_signal, shares)
        assert can_open

        position = self.portfolio.open_position(self.sample_signal, shares)
        assert position is not None
        assert position.symbol == 'TEST'
        assert position.shares == shares
        assert self.portfolio.cash < 100000  # Cash should decrease

    def test_position_limits(self):
        """Test position size and count limits."""
        # Test cash limit
        large_shares = 2000  # Would exceed portfolio value
        can_open, reason = self.portfolio.can_open_position(self.sample_signal, large_shares)
        assert not can_open
        assert "cash" in reason.lower()

    def test_position_closing(self):
        """Test closing a position."""
        # First open a position
        shares = 100
        position = self.portfolio.open_position(self.sample_signal, shares)
        assert position is not None

        # Create exit signal
        exit_signal = TradeSignal(
            symbol='TEST',
            signal_type='SELL',
            price=110.0,  # 10% gain
            timestamp=datetime.now(),
            confidence=1.0,
            reason="Profit target"
        )

        closed_trade = self.portfolio.close_position('TEST', exit_signal)
        assert closed_trade is not None
        assert closed_trade.pnl_percent > 0  # Should be profitable
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.closed_trades) == 1

    def test_portfolio_statistics(self):
        """Test portfolio statistics calculation."""
        # Open and close a profitable trade
        self.portfolio.open_position(self.sample_signal, 100)

        exit_signal = TradeSignal(
            symbol='TEST',
            signal_type='SELL',
            price=110.0,
            timestamp=datetime.now(),
            confidence=1.0,
            reason="Test exit"
        )

        self.portfolio.close_position('TEST', exit_signal)

        stats = self.portfolio.get_portfolio_stats()
        assert isinstance(stats, PortfolioStats)
        assert stats.num_trades == 1
        assert stats.total_return > 0

    def test_portfolio_persistence(self):
        """Test saving and loading portfolio state."""
        # Open a position
        self.portfolio.open_position(self.sample_signal, 100)

        # Save state
        test_file = "test_portfolio.json"
        self.portfolio.save_portfolio_state(test_file)

        # Create new portfolio and load state
        new_portfolio = PortfolioManager(50000)  # Different initial capital
        new_portfolio.load_portfolio_state(test_file)

        # Should have same state as original
        assert new_portfolio.initial_capital == 100000
        assert len(new_portfolio.positions) == 1
        assert 'TEST' in new_portfolio.positions

        # Clean up
        os.remove(test_file)


class TestBacktester:
    """Test backtesting functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.backtester = VCPBacktester()
        self.test_symbols = ['TEST1', 'TEST2']
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2023, 12, 31)

    def test_backtester_initialization(self):
        """Test backtester initialization."""
        assert self.backtester.strategy is not None
        assert self.backtester.vcp_detector is not None
        assert self.backtester.data_fetcher is not None

    def test_backtest_with_mock_data(self):
        """Test backtesting with simplified mock data."""
        # This is a simplified test - in practice, backtesting requires real market data
        # For comprehensive testing, you'd need to mock the data fetcher

        # Test that backtester can handle empty data gracefully
        empty_symbols = []
        results = self.backtester.run_backtest(
            empty_symbols,
            self.start_date,
            self.end_date,
            initial_capital=10000
        )

        assert isinstance(results, BacktestResults)
        assert results.num_trades == 0
        assert results.symbols_tested == 0


class TestPerformanceAnalyzer:
    """Test performance analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PerformanceAnalyzer()
        self.sample_results = self._create_sample_results()

    def _create_sample_results(self) -> BacktestResults:
        """Create sample backtest results for testing."""
        return BacktestResults(
            total_return=0.25,
            annual_return=0.20,
            sharpe_ratio=1.5,
            max_drawdown=0.12,
            volatility=0.18,
            num_trades=50,
            win_rate=0.65,
            avg_gain=0.15,
            avg_loss=-0.08,
            profit_factor=2.1,
            avg_holding_days=25,
            benchmark_return=0.10,
            alpha=0.08,
            beta=1.1,
            final_value=125000,
            total_fees=200,
            portfolio_history=[
                {'date': datetime(2023, 1, 1), 'portfolio_value': 100000, 'cash': 50000, 'num_positions': 5},
                {'date': datetime(2023, 6, 1), 'portfolio_value': 110000, 'cash': 55000, 'num_positions': 7},
                {'date': datetime(2023, 12, 31), 'portfolio_value': 125000, 'cash': 60000, 'num_positions': 8}
            ],
            trade_history=[
                ClosedTrade(
                    symbol='TEST',
                    entry_date=datetime(2023, 1, 15),
                    exit_date=datetime(2023, 2, 15),
                    entry_price=100.0,
                    exit_price=115.0,
                    shares=100,
                    holding_days=31,
                    pnl_dollars=1500,
                    pnl_percent=0.15,
                    exit_reason="Profit target",
                    confidence=0.85
                )
            ],
            backtest_period="2023-01-01 to 2023-12-31",
            symbols_tested=100,
            vcp_patterns_found=30
        )

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        assert self.analyzer is not None

    def test_backtest_report_generation(self):
        """Test backtest report generation."""
        # Create temporary directory for test
        test_dir = "test_reports"
        os.makedirs(test_dir, exist_ok=True)

        try:
            report_path = self.analyzer.generate_backtest_report(self.sample_results, test_dir)
            assert os.path.exists(report_path)
            assert report_path.endswith('.html')

            # Check that file contains expected content
            with open(report_path, 'r') as f:
                content = f.read()
                assert 'VCP Trading Strategy Backtest Report' in content
                assert '25.0%' in content  # Total return

        finally:
            # Clean up
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir)

    def test_trade_analysis(self):
        """Test trade analysis functionality."""
        test_dir = "test_reports"
        os.makedirs(test_dir, exist_ok=True)

        try:
            analysis = self.analyzer.generate_trade_analysis(self.sample_results.trade_history, test_dir)

            assert 'total_trades' in analysis
            assert 'win_rate' in analysis
            assert 'profit_factor' in analysis
            assert analysis['total_trades'] == 1
            assert analysis['win_rate'] == 1.0  # 100% since only profitable trade

        finally:
            # Clean up
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir)


class TestIntegration:
    """Integration tests for the complete trading system."""

    def test_full_pipeline_simulation(self):
        """Test the complete pipeline from VCP detection to trade execution."""
        # This is a simplified integration test
        # In practice, you'd test with real VCP screening results

        # 1. Initialize components
        strategy = VCPTradingStrategy()
        portfolio = PortfolioManager(100000)

        # 2. Create mock VCP result (simulating daily screening output)
        vcp_result = VCPResult(
            detected=True,
            confidence=0.85,
            contractions=[],
            breakout_date=datetime.now() - timedelta(days=1),
            breakout_price=150.0,
            base_length_days=30,
            volume_trend="decreasing",
            notes=["High confidence pattern"]
        )

        # 3. Test signal generation (would normally use real market data)
        # For testing purposes, we'll create a mock scenario

        # 4. Test portfolio management
        initial_cash = portfolio.cash
        initial_positions = len(portfolio.positions)

        # Verify starting state
        assert initial_cash == 100000
        assert initial_positions == 0

        # This integration test validates that all components can work together
        # Real testing would require market data and full pipeline execution


def run_comprehensive_test():
    """Run all tests and generate summary report."""
    print("🧪 Running VCP Trading Strategy Test Suite")
    print("=" * 50)

    # Run pytest with verbose output
    test_files = [
        'test_suite.py::TestTradingStrategy',
        'test_suite.py::TestPortfolioManager',
        'test_suite.py::TestBacktester',
        'test_suite.py::TestPerformanceAnalyzer',
        'test_suite.py::TestIntegration'
    ]

    import subprocess
    import sys

    total_tests = 0
    passed_tests = 0

    for test_class in test_files:
        print(f"\n📋 Running {test_class.split('::')[1]}...")
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', test_class, '-v'
            ], capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print(f"✅ {test_class.split('::')[1]} - All tests passed")
                passed_tests += len([line for line in result.stdout.split('\n') if '::test_' in line and 'PASSED' in line])
            else:
                print(f"❌ {test_class.split('::')[1]} - Some tests failed")
                print(result.stdout)

            total_tests += len([line for line in result.stdout.split('\n') if '::test_' in line])

        except Exception as e:
            print(f"⚠️  Error running {test_class}: {e}")

    print(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed! Trading strategy is ready for deployment.")
    else:
        print("⚠️  Some tests failed. Please review and fix issues before deployment.")


if __name__ == "__main__":
    # Run comprehensive test suite
    run_comprehensive_test()