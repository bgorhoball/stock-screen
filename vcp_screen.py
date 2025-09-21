#!/usr/bin/env python3
"""
Main VCP screening script for S&P 500 stocks.

This script fetches S&P 500 ticker data, applies VCP pattern detection,
and generates reports with the results.
"""

import argparse
import logging
import os
import sys
import time
import yaml
from datetime import datetime
from typing import Dict, List

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ticker_fetcher import SP500TickerFetcher
from data_fetcher import DataFetcher
from vcp_detector import VCPDetector
from report_generator import ReportGenerator
from telegram_bot import TelegramBot


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.warning(f"Config file {config_path} not found, using defaults")
        return {}


def main():
    """Main screening function."""
    parser = argparse.ArgumentParser(description="VCP Pattern Screening for S&P 500")
    parser.add_argument('--input', '-i', type=str,
                       help='Input file with ticker symbols (one per line)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output directory for reports')
    parser.add_argument('--config', '-c', type=str, default='config/config.yaml',
                       help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--max-symbols', '-m', type=int,
                       help='Maximum number of symbols to process (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run - fetch data but skip analysis')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting VCP screening process...")
    start_time = time.time()

    try:
        # Load configuration
        config = load_config(args.config)

        # Initialize components
        ticker_fetcher = SP500TickerFetcher()
        data_fetcher = DataFetcher()
        vcp_detector = VCPDetector(config.get('vcp_parameters', {}))
        telegram_bot = TelegramBot()

        output_dir = args.output or 'daily_reports'
        report_generator = ReportGenerator(output_dir)

        # Get ticker symbols
        if args.input:
            logger.info(f"Loading tickers from {args.input}")
            symbols = ticker_fetcher.load_tickers_from_file(args.input)
        else:
            logger.info("Fetching S&P 500 tickers...")
            symbols = ticker_fetcher.get_sp500_tickers()

        # Limit symbols for testing
        if args.max_symbols:
            symbols = symbols[:args.max_symbols]
            logger.info(f"Limited to {len(symbols)} symbols for testing")

        logger.info(f"Processing {len(symbols)} symbols...")

        # Fetch historical data
        logger.info("Fetching historical data...")
        screening_config = config.get('screening', {})
        historical_weeks = screening_config.get('historical_weeks', 12)

        stock_data = data_fetcher.fetch_multiple_stocks(symbols, weeks=historical_weeks)
        data_summary = data_fetcher.get_data_summary(stock_data)

        logger.info(f"Successfully fetched data for {len(stock_data)} symbols")

        if args.dry_run:
            logger.info("Dry run complete - skipping VCP analysis")
            return

        # Apply VCP screening
        logger.info("Applying VCP pattern detection...")
        vcp_results = {}

        for i, (symbol, data) in enumerate(stock_data.items()):
            if data_fetcher.validate_data_quality(data, symbol):
                result = vcp_detector.detect_vcp(data, symbol)
                vcp_results[symbol] = result

                if result.detected:
                    logger.info(f"VCP detected for {symbol} (confidence: {result.confidence:.2f})")
            else:
                logger.warning(f"Skipping {symbol} due to poor data quality")

            # Progress update
            if (i + 1) % 50 == 0:
                logger.info(f"VCP analysis progress: {i+1}/{len(stock_data)} symbols")

        # Generate reports
        logger.info("Generating reports...")

        # CSV report
        timestamp = datetime.now().strftime("%Y%m%d")
        csv_filename = f"vcp_matches_{timestamp}.csv"
        csv_path = report_generator.generate_csv_report(vcp_results, csv_filename)

        # Summary report
        execution_time = time.time() - start_time
        summary = report_generator.generate_summary_report(
            vcp_results, data_summary, execution_time
        )

        # Save summary as JSON
        json_filename = f"vcp_summary_{timestamp}.json"
        json_path = report_generator.save_summary_json(summary, json_filename)

        # Print summary to console
        report_generator.print_summary_to_console(summary)

        # Create GitHub issue content for notifications
        detected_vcps = [
            {
                'symbol': symbol,
                'confidence': result.confidence,
                'contractions_count': len(result.contractions),
                'base_length_days': result.base_length_days,
                'volume_trend': result.volume_trend,
                'breakout_detected': result.breakout_date is not None
            }
            for symbol, result in vcp_results.items()
            if result.detected
        ]

        # Sort by confidence
        detected_vcps.sort(key=lambda x: x['confidence'], reverse=True)

        github_content = report_generator.create_github_issue_content(
            summary, detected_vcps
        )

        # Save GitHub content
        github_filename = f"github_report_{timestamp}.md"
        github_path = os.path.join(output_dir, github_filename)
        with open(github_path, 'w') as f:
            f.write(github_content)

        logger.info(f"Reports generated:")
        logger.info(f"  CSV: {csv_path}")
        logger.info(f"  Summary JSON: {json_path}")
        logger.info(f"  GitHub report: {github_path}")

        # Send Telegram notification
        if telegram_bot.enabled:
            logger.info("Sending Telegram notification...")
            try:
                telegram_success = telegram_bot.send_daily_screening_report(summary, detected_vcps)
                if telegram_success:
                    logger.info("✅ Telegram notification sent successfully")
                else:
                    logger.warning("❌ Failed to send Telegram notification")
            except Exception as e:
                logger.error(f"Error sending Telegram notification: {e}")

        # Final summary
        detected_count = summary['vcp_patterns_detected']
        high_confidence = summary['high_confidence_matches']

        if detected_count > 0:
            logger.info(f"🎯 SCREENING COMPLETE: {detected_count} VCP patterns detected "
                       f"({high_confidence} high confidence)")
        else:
            logger.info("📊 SCREENING COMPLETE: No VCP patterns detected today")

        logger.info(f"Total execution time: {execution_time:.1f} seconds")

    except KeyboardInterrupt:
        logger.info("Screening interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Screening failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()