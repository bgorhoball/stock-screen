"""
Standalone VCP Trading Strategy Backtesting Script
Run comprehensive backtests with real historical data and generate performance reports
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# Add src directory to path
sys.path.append('src')

from src.backtester import VCPBacktester
from src.performance_analyzer import PerformanceAnalyzer
from src.ticker_fetcher import SP500TickerFetcher

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('backtest.log')
        ]
    )

def get_test_symbols(symbol_source: str, max_symbols: int = None) -> List[str]:
    """
    Get symbols for backtesting.

    Args:
        symbol_source: 'sp500', 'top100', 'custom', or comma-separated symbols
        max_symbols: Maximum number of symbols to test

    Returns:
        List of stock symbols
    """
    if symbol_source == 'sp500':
        print("📊 Fetching S&P 500 symbols...")
        fetcher = SP500TickerFetcher()
        symbols = fetcher.get_sp500_tickers()
        print(f"✅ Fetched {len(symbols)} S&P 500 symbols")

    elif symbol_source == 'top100':
        # Popular large-cap stocks for testing
        symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B',
            'JNJ', 'V', 'WMT', 'PG', 'JPM', 'UNH', 'HD', 'MA', 'BAC', 'ABBV',
            'PFE', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'DIS', 'ABT', 'ACN',
            'ADBE', 'DHR', 'VZ', 'NEE', 'BMY', 'TXN', 'QCOM', 'LLY', 'MDT',
            'PM', 'AMGN', 'CRM', 'HON', 'UNP', 'ORCL', 'LOW', 'IBM', 'C',
            'RTX', 'BA', 'SBUX', 'CVX', 'BLK', 'CAT', 'GE', 'AMT', 'AXP',
            'GILD', 'MCD', 'DE', 'SCHW', 'AMAT', 'LRCX', 'SYK', 'TJX', 'NOW',
            'BSX', 'ZTS', 'CI', 'ISRG', 'CVS', 'MMM', 'ADP', 'SO', 'PLD',
            'BKNG', 'REGN', 'DUK', 'AON', 'CL', 'APD', 'EQIX', 'ITW', 'SHW',
            'CME', 'MU', 'NSC', 'EOG', 'CSX', 'WM', 'FCX', 'ETN', 'ICE',
            'PNC', 'ADI', 'USB', 'COP', 'D', 'GD', 'ATVI', 'EMR', 'FDX'
        ]
        print(f"📊 Using top 100 large-cap symbols ({len(symbols)} symbols)")

    elif symbol_source == 'vcp_candidates':
        # Use VCP candidates from recent screening
        symbols = [
            'CDNS', 'WFC', 'BIIB', 'OXY', 'ETN', 'PCAR', 'AAPL', 'AMZN',
            # Add more from your VCP screening results
        ]
        print(f"📊 Using VCP candidate symbols ({len(symbols)} symbols)")

    else:
        # Custom symbols (comma-separated)
        symbols = [s.strip().upper() for s in symbol_source.split(',')]
        print(f"📊 Using custom symbols: {symbols}")

    # Limit symbols if specified
    if max_symbols and len(symbols) > max_symbols:
        symbols = symbols[:max_symbols]
        print(f"🔢 Limited to {max_symbols} symbols for testing")

    return symbols

def run_backtest(config: Dict) -> None:
    """
    Run comprehensive backtest with specified configuration.

    Args:
        config: Backtest configuration dictionary
    """
    print(f"\n🚀 Starting VCP Strategy Backtest")
    print(f"📅 Period: {config['start_date'].date()} to {config['end_date'].date()}")
    print(f"💰 Initial Capital: ${config['initial_capital']:,}")
    print(f"📊 Symbols: {len(config['symbols'])} symbols")

    # Initialize backtester
    print("\n🔧 Initializing backtester...")
    backtester = VCPBacktester(
        strategy_config=config.get('strategy_config'),
        portfolio_config=config.get('portfolio_config')
    )

    # Run backtest
    print("\n📈 Running backtest (this may take several minutes)...")
    start_time = datetime.now()

    results = backtester.run_backtest(
        symbols=config['symbols'],
        start_date=config['start_date'],
        end_date=config['end_date'],
        initial_capital=config['initial_capital']
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n✅ Backtest completed in {duration:.1f} seconds")

    # Display results summary
    print_results_summary(results)

    # Generate detailed reports
    if config.get('generate_reports', True):
        print("\n📋 Generating detailed reports...")
        generate_reports(results, config)

def print_results_summary(results) -> None:
    """Print backtest results summary to console."""
    print(f"\n{'='*60}")
    print(f"📊 VCP STRATEGY BACKTEST RESULTS")
    print(f"{'='*60}")

    print(f"\n📈 PERFORMANCE METRICS")
    print(f"Total Return:      {results.total_return:>8.1%}")
    print(f"Annual Return:     {results.annual_return:>8.1%}")
    print(f"Benchmark (SPY):   {results.benchmark_return:>8.1%}")
    print(f"Alpha:             {results.alpha:>8.1%}")
    print(f"Beta:              {results.beta:>8.2f}")

    print(f"\n⚠️  RISK METRICS")
    print(f"Max Drawdown:      {results.max_drawdown:>8.1%}")
    print(f"Sharpe Ratio:      {results.sharpe_ratio:>8.2f}")
    print(f"Volatility:        {results.volatility:>8.1%}")

    print(f"\n📊 TRADING STATISTICS")
    print(f"Total Trades:      {results.num_trades:>8}")
    print(f"Win Rate:          {results.win_rate:>8.1%}")
    print(f"Avg Gain:          {results.avg_gain:>8.1%}")
    print(f"Avg Loss:          {results.avg_loss:>8.1%}")
    print(f"Profit Factor:     {results.profit_factor:>8.2f}")
    print(f"Avg Hold Days:     {results.avg_holding_days:>8.1f}")

    print(f"\n💰 PORTFOLIO SUMMARY")
    print(f"Final Value:       ${results.final_value:>11,.0f}")
    print(f"Total Fees:        ${results.total_fees:>11,.0f}")
    print(f"Symbols Tested:    {results.symbols_tested:>8}")
    print(f"VCP Patterns:      {results.vcp_patterns_found:>8}")

    # Performance assessment
    print(f"\n🎯 PERFORMANCE ASSESSMENT")

    if results.total_return > 0.15:  # 15%+ return
        if results.sharpe_ratio > 1.0:
            assessment = "🌟 EXCELLENT - High returns with good risk management"
        else:
            assessment = "👍 GOOD - High returns but higher volatility"
    elif results.total_return > 0.08:  # 8%+ return
        if results.sharpe_ratio > 0.8:
            assessment = "✅ SOLID - Decent returns with reasonable risk"
        else:
            assessment = "⚠️  MODERATE - Returns acceptable but risky"
    else:
        assessment = "❌ POOR - Low returns, strategy needs improvement"

    print(f"Overall Rating: {assessment}")

    # Strategy recommendations
    print(f"\n💡 RECOMMENDATIONS")

    if results.win_rate < 0.5:
        print("• Consider tightening entry criteria (higher confidence threshold)")

    if results.max_drawdown > 0.2:
        print("• Consider reducing position sizes or adding risk controls")

    if results.avg_holding_days > 60:
        print("• Consider adding time-based exit rules")

    if results.profit_factor < 1.5:
        print("• Review exit strategy - may be cutting winners too early")

def generate_reports(results, config: Dict) -> None:
    """Generate detailed reports and charts."""
    analyzer = PerformanceAnalyzer()

    # Create reports directory
    reports_dir = config.get('reports_dir', 'backtest_reports')
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Generate HTML report
        print("📄 Generating HTML report...")
        html_report = analyzer.generate_backtest_report(results, reports_dir)
        print(f"✅ HTML report: {html_report}")

        # Generate trade analysis
        if results.trade_history:
            print("📊 Generating trade analysis...")
            trade_analysis = analyzer.generate_trade_analysis(results.trade_history, reports_dir)
            print(f"✅ Trade analysis completed")

        # Generate performance charts
        print("📈 Generating performance charts...")
        chart_paths = analyzer.create_performance_charts(results, reports_dir)
        print(f"✅ Generated {len(chart_paths)} performance charts")

        # Summary
        print(f"\n📁 All reports saved to: {reports_dir}/")

    except Exception as e:
        print(f"⚠️  Error generating reports: {e}")
        logging.error(f"Report generation error: {e}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='VCP Trading Strategy Backtester')

    # Backtest parameters
    parser.add_argument('--symbols', default='top100',
                       help='Symbol source: sp500, top100, vcp_candidates, or comma-separated list')
    parser.add_argument('--max-symbols', type=int, default=None,
                       help='Maximum number of symbols to test')
    parser.add_argument('--start-date', default='2022-01-01',
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2024-01-01',
                       help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000,
                       help='Initial capital for backtest')

    # Strategy configuration
    parser.add_argument('--min-confidence', type=float, default=0.8,
                       help='Minimum VCP confidence for entry')
    parser.add_argument('--stop-loss', type=float, default=0.08,
                       help='Stop loss percentage (0.08 = 8%)')
    parser.add_argument('--profit-target', type=float, default=0.25,
                       help='Profit target percentage (0.25 = 25%)')
    parser.add_argument('--max-positions', type=int, default=15,
                       help='Maximum concurrent positions')

    # Output options
    parser.add_argument('--reports-dir', default='backtest_reports',
                       help='Directory for output reports')
    parser.add_argument('--no-reports', action='store_true',
                       help='Skip detailed report generation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        sys.exit(1)

    # Validate date range
    if start_date >= end_date:
        print("❌ Start date must be before end date")
        sys.exit(1)

    if end_date > datetime.now():
        print("❌ End date cannot be in the future")
        sys.exit(1)

    # Get symbols
    try:
        symbols = get_test_symbols(args.symbols, args.max_symbols)
    except Exception as e:
        print(f"❌ Error fetching symbols: {e}")
        sys.exit(1)

    if not symbols:
        print("❌ No symbols found for backtesting")
        sys.exit(1)

    # Build configuration
    config = {
        'symbols': symbols,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': args.capital,
        'strategy_config': {
            'min_confidence': args.min_confidence,
            'stop_loss_percent': args.stop_loss,
            'profit_target_percent': args.profit_target,
            'max_positions': args.max_positions
        },
        'portfolio_config': {
            'max_positions': args.max_positions,
            'commission': 1.0,
            'slippage': 0.001
        },
        'reports_dir': args.reports_dir,
        'generate_reports': not args.no_reports
    }

    # Run backtest
    try:
        run_backtest(config)
        print(f"\n🎉 Backtesting completed successfully!")

    except KeyboardInterrupt:
        print(f"\n⚠️  Backtest interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        logging.error(f"Backtest error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()