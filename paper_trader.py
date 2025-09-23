"""
Paper Trading Simulation for VCP Strategy
Simulates live trading with real market data without actual money
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse

# Add src directory to path
sys.path.append('src')

from src.trading_strategy import VCPTradingStrategy, TradeSignal
from src.portfolio_manager import PortfolioManager
from src.vcp_detector import VCPDetector
from src.data_fetcher import DataFetcher
from src.telegram_bot import TelegramBot
from src.performance_analyzer import PerformanceAnalyzer

class PaperTrader:
    """Paper trading simulation for VCP strategy."""

    def __init__(self, initial_capital: float = 100000, config: Dict = None):
        """
        Initialize paper trader.

        Args:
            initial_capital: Starting capital for simulation
            config: Configuration dictionary
        """
        self.config = config or {}

        # Initialize components
        self.strategy = VCPTradingStrategy(self.config.get('strategy', {}))
        self.portfolio = PortfolioManager(initial_capital, self.config.get('portfolio', {}))
        self.vcp_detector = VCPDetector()
        self.data_fetcher = DataFetcher()
        self.telegram_bot = TelegramBot()
        self.analyzer = PerformanceAnalyzer()

        # State management
        self.portfolio_file = self.config.get('portfolio_file', 'paper_portfolio.json')
        self.watchlist_file = self.config.get('watchlist_file', 'paper_watchlist.json')
        self.alerts_file = self.config.get('alerts_file', 'paper_alerts.json')

        # Load existing state
        self.load_state()

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for paper trader."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('paper_trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PaperTrader')

    def load_state(self):
        """Load paper trading state from files."""
        # Load portfolio state
        if os.path.exists(self.portfolio_file):
            try:
                self.portfolio.load_portfolio_state(self.portfolio_file)
                self.logger.info(f"Loaded portfolio state from {self.portfolio_file}")
            except Exception as e:
                self.logger.error(f"Error loading portfolio state: {e}")

        # Load watchlist
        self.watchlist = []
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r') as f:
                    self.watchlist = json.load(f)
                self.logger.info(f"Loaded {len(self.watchlist)} symbols from watchlist")
            except Exception as e:
                self.logger.error(f"Error loading watchlist: {e}")

    def save_state(self):
        """Save paper trading state to files."""
        try:
            # Save portfolio state
            self.portfolio.save_portfolio_state(self.portfolio_file)

            # Save watchlist
            with open(self.watchlist_file, 'w') as f:
                json.dump(self.watchlist, f, indent=2)

            self.logger.info("Paper trading state saved successfully")

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def add_to_watchlist(self, symbols: List[str]):
        """Add symbols to paper trading watchlist."""
        new_symbols = []
        for symbol in symbols:
            if symbol not in self.watchlist:
                self.watchlist.append(symbol)
                new_symbols.append(symbol)

        if new_symbols:
            self.logger.info(f"Added {len(new_symbols)} symbols to watchlist: {new_symbols}")
            self.save_state()

    def process_vcp_candidates(self, vcp_candidates_file: str = None):
        """
        Process VCP candidates from daily screening and add high-confidence ones to watchlist.

        Args:
            vcp_candidates_file: Path to VCP candidates JSON file
        """
        if not vcp_candidates_file:
            vcp_candidates_file = 'daily_reports/vcp_monitoring_candidates.json'

        if not os.path.exists(vcp_candidates_file):
            self.logger.warning(f"VCP candidates file not found: {vcp_candidates_file}")
            return

        try:
            with open(vcp_candidates_file, 'r') as f:
                data = json.load(f)

            candidates = data.get('candidates', [])
            high_confidence_symbols = [
                candidate['symbol'] for candidate in candidates
                if candidate.get('confidence', 0) >= self.strategy.config['min_confidence']
            ]

            if high_confidence_symbols:
                self.add_to_watchlist(high_confidence_symbols)
                self.logger.info(f"Added {len(high_confidence_symbols)} high-confidence VCP candidates")

                # Send Telegram notification
                if self.telegram_bot.enabled:
                    message = f"📊 Paper Trading Update\n"
                    message += f"Added {len(high_confidence_symbols)} VCP candidates to watchlist:\n"
                    message += ", ".join(high_confidence_symbols[:10])  # First 10 symbols
                    if len(high_confidence_symbols) > 10:
                        message += f" and {len(high_confidence_symbols) - 10} more..."

                    self.telegram_bot.send_message(message)

        except Exception as e:
            self.logger.error(f"Error processing VCP candidates: {e}")

    def scan_for_entries(self):
        """Scan watchlist for entry opportunities."""
        entry_signals = []

        self.logger.info(f"Scanning {len(self.watchlist)} symbols for entry opportunities...")

        for symbol in self.watchlist[:]:  # Copy list to allow modification
            try:
                # Skip if already have position
                if symbol in self.portfolio.positions:
                    continue

                # Get recent data for analysis
                data = self.data_fetcher.fetch_stock_data(symbol, weeks=12)
                if data is None or len(data) < 84:  # Need ~12 weeks
                    continue

                # Run VCP detection
                vcp_result = self.vcp_detector.detect_vcp(data, symbol)

                if vcp_result.detected and vcp_result.breakout_date:
                    # Check if breakout is recent (within last 3 days)
                    days_since_breakout = (datetime.now() - vcp_result.breakout_date).days
                    if days_since_breakout <= 3:

                        # Generate trading signal
                        signal = self.strategy.analyze_vcp_signal(vcp_result, symbol, data)

                        if signal:
                            entry_signals.append(signal)
                            self.logger.info(f"Entry signal: {symbol} at ${signal.price:.2f}")

            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {e}")

        return entry_signals

    def scan_for_exits(self):
        """Scan current positions for exit opportunities."""
        exit_signals = []

        self.logger.info(f"Scanning {len(self.portfolio.positions)} positions for exits...")

        for symbol, position in self.portfolio.positions.items():
            try:
                # Get current price
                data = self.data_fetcher.fetch_stock_data(symbol, weeks=1)
                if data is None or data.empty:
                    continue

                current_price = data['close'].iloc[-1]

                # Check for exit signal
                exit_signal = self.strategy.should_exit_position(position, current_price)

                if exit_signal:
                    exit_signals.append(exit_signal)
                    self.logger.info(f"Exit signal: {symbol} at ${exit_signal.price:.2f} - {exit_signal.reason}")

            except Exception as e:
                self.logger.error(f"Error checking exit for {symbol}: {e}")

        return exit_signals

    def execute_entries(self, entry_signals: List[TradeSignal]):
        """Execute entry signals."""
        executed_entries = []

        for signal in entry_signals:
            try:
                # Calculate position size
                portfolio_value = self.portfolio.get_portfolio_value()
                shares = self.strategy.calculate_position_size(signal, portfolio_value)

                if shares > 0:
                    # Execute entry
                    position = self.portfolio.open_position(signal, shares)

                    if position:
                        executed_entries.append((signal, position))
                        self.logger.info(f"✅ Entered {signal.symbol}: {shares} shares at ${signal.price:.2f}")

                        # Remove from watchlist (we now have a position)
                        if signal.symbol in self.watchlist:
                            self.watchlist.remove(signal.symbol)

            except Exception as e:
                self.logger.error(f"Error executing entry for {signal.symbol}: {e}")

        return executed_entries

    def execute_exits(self, exit_signals: List[TradeSignal]):
        """Execute exit signals."""
        executed_exits = []

        for signal in exit_signals:
            try:
                # Execute exit
                closed_trade = self.portfolio.close_position(signal.symbol, signal)

                if closed_trade:
                    executed_exits.append((signal, closed_trade))
                    self.logger.info(f"✅ Exited {signal.symbol}: {closed_trade.pnl_percent:.1%} "
                                   f"({closed_trade.pnl_dollars:.0f}) - {signal.reason}")

                    # Add back to watchlist for future monitoring
                    if closed_trade.pnl_percent > 0:  # Only re-add if profitable
                        self.add_to_watchlist([signal.symbol])

            except Exception as e:
                self.logger.error(f"Error executing exit for {signal.symbol}: {e}")

        return executed_exits

    def send_trading_alerts(self, entries: List, exits: List):
        """Send trading alerts via Telegram."""
        if not self.telegram_bot.enabled:
            return

        if not entries and not exits:
            return

        message = "📈 Paper Trading Alert\n"
        message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n\n"

        # Entry alerts
        if entries:
            message += f"🟢 NEW POSITIONS ({len(entries)}):\n"
            for signal, position in entries:
                message += f"• {signal.symbol}: {position.shares} shares @ ${signal.price:.2f}\n"
                message += f"  Stop: ${signal.stop_loss:.2f} | Target: ${signal.profit_target:.2f}\n"

        # Exit alerts
        if exits:
            message += f"\n🔴 CLOSED POSITIONS ({len(exits)}):\n"
            for signal, trade in exits:
                pnl_emoji = "💰" if trade.pnl_percent > 0 else "📉"
                message += f"• {signal.symbol}: {pnl_emoji} {trade.pnl_percent:.1%} "
                message += f"(${trade.pnl_dollars:.0f}) - {signal.reason}\n"

        # Portfolio summary
        stats = self.portfolio.get_portfolio_stats()
        message += f"\n💼 PORTFOLIO:\n"
        message += f"Value: ${stats.total_value:,.0f} ({stats.total_return:.1%})\n"
        message += f"Positions: {stats.num_positions} | Cash: ${stats.cash:,.0f}\n"

        try:
            self.telegram_bot.send_message(message)
        except Exception as e:
            self.logger.error(f"Error sending Telegram alert: {e}")

    def run_trading_cycle(self):
        """Run one complete trading cycle."""
        self.logger.info("🔄 Starting paper trading cycle...")

        # 1. Process new VCP candidates
        self.process_vcp_candidates()

        # 2. Scan for entry opportunities
        entry_signals = self.scan_for_entries()

        # 3. Scan for exit opportunities
        exit_signals = self.scan_for_exits()

        # 4. Execute trades
        executed_entries = self.execute_entries(entry_signals)
        executed_exits = self.execute_exits(exit_signals)

        # 5. Update portfolio with current prices
        self.update_portfolio_prices()

        # 6. Save state
        self.save_state()

        # 7. Send alerts
        self.send_trading_alerts(executed_entries, executed_exits)

        # 8. Log summary
        self.log_cycle_summary(executed_entries, executed_exits)

        self.logger.info("✅ Paper trading cycle completed")

    def update_portfolio_prices(self):
        """Update current prices for all positions."""
        if not self.portfolio.positions:
            return

        current_prices = {}
        for symbol in self.portfolio.positions.keys():
            try:
                data = self.data_fetcher.fetch_stock_data(symbol, weeks=1)
                if data is not None and not data.empty:
                    current_prices[symbol] = data['close'].iloc[-1]
            except Exception as e:
                self.logger.error(f"Error updating price for {symbol}: {e}")

        if current_prices:
            self.portfolio.update_positions(current_prices)

    def log_cycle_summary(self, entries: List, exits: List):
        """Log summary of trading cycle."""
        stats = self.portfolio.get_portfolio_stats()

        self.logger.info(f"📊 Trading Cycle Summary:")
        self.logger.info(f"  New Entries: {len(entries)}")
        self.logger.info(f"  Exits: {len(exits)}")
        self.logger.info(f"  Open Positions: {stats.num_positions}")
        self.logger.info(f"  Portfolio Value: ${stats.total_value:,.0f}")
        self.logger.info(f"  Total Return: {stats.total_return:.1%}")
        self.logger.info(f"  Win Rate: {stats.win_rate:.1%}")

    def generate_performance_report(self):
        """Generate performance report for paper trading."""
        stats = self.portfolio.get_portfolio_stats()
        positions = self.portfolio.get_position_summary()
        recent_trades = self.portfolio.get_trade_history(limit=20)

        summary = self.analyzer.generate_live_performance_summary(self.portfolio)

        # Create detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_summary': {
                'total_value': stats.total_value,
                'total_return': stats.total_return,
                'cash': stats.cash,
                'invested': stats.invested,
                'num_positions': stats.num_positions,
                'unrealized_pnl': stats.unrealized_pnl,
                'realized_pnl': stats.realized_pnl
            },
            'trading_stats': {
                'num_trades': stats.num_trades,
                'win_rate': stats.win_rate,
                'avg_gain': stats.avg_gain,
                'avg_loss': stats.avg_loss,
                'sharpe_ratio': stats.sharpe_ratio,
                'max_drawdown': stats.max_drawdown
            },
            'current_positions': positions,
            'recent_trades': recent_trades,
            'watchlist_size': len(self.watchlist)
        }

        # Save report
        report_file = f"paper_trading_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Performance report saved: {report_file}")
        return report

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='VCP Paper Trading Simulation')

    parser.add_argument('--capital', type=float, default=100000,
                       help='Initial capital for paper trading')
    parser.add_argument('--mode', choices=['single', 'monitor'], default='single',
                       help='Run mode: single cycle or continuous monitoring')
    parser.add_argument('--interval', type=int, default=300,
                       help='Monitoring interval in seconds (default: 5 minutes)')
    parser.add_argument('--vcp-file',
                       help='Path to VCP candidates file')
    parser.add_argument('--config-file',
                       help='Path to configuration file')
    parser.add_argument('--report', action='store_true',
                       help='Generate performance report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    # Load configuration
    config = {}
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r') as f:
            config = json.load(f)

    # Initialize paper trader
    trader = PaperTrader(initial_capital=args.capital, config=config)

    try:
        if args.mode == 'single':
            # Run single trading cycle
            print("🎯 Running single paper trading cycle...")
            trader.run_trading_cycle()

            if args.report:
                print("📊 Generating performance report...")
                trader.generate_performance_report()

        elif args.mode == 'monitor':
            # Continuous monitoring mode
            print(f"🔄 Starting continuous paper trading (interval: {args.interval}s)")
            print("Press Ctrl+C to stop monitoring...")

            while True:
                try:
                    trader.run_trading_cycle()
                    time.sleep(args.interval)

                except KeyboardInterrupt:
                    print("\n⚠️  Monitoring stopped by user")
                    break

        print("✅ Paper trading completed")

    except Exception as e:
        print(f"❌ Paper trading error: {e}")
        logging.error(f"Paper trading error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()