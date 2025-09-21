"""
Historical stock data fetching with multiple API failover support.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import os
from typing import Dict, List, Optional, Tuple
from alpha_vantage.timeseries import TimeSeries
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DataFetcher:
    """Fetches historical stock data with failover between multiple APIs."""

    def __init__(self):
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.av_ts = TimeSeries(key=self.alpha_vantage_key) if self.alpha_vantage_key else None
        self.request_count = 0
        self.last_request_time = 0

    def fetch_stock_data(self,
                        symbol: str,
                        weeks: int = 12,
                        use_fallback: bool = True) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data for a given symbol.

        Args:
            symbol: Stock ticker symbol
            weeks: Number of weeks of historical data to fetch
            use_fallback: Whether to use Alpha Vantage as fallback

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            # Primary: yfinance
            data = self._fetch_from_yfinance(symbol, weeks)
            if data is not None and len(data) > 0:
                return data
        except Exception as e:
            logger.warning(f"yfinance failed for {symbol}: {e}")

        if use_fallback and self.av_ts:
            try:
                # Fallback: Alpha Vantage
                return self._fetch_from_alpha_vantage(symbol, weeks)
            except Exception as e:
                logger.warning(f"Alpha Vantage failed for {symbol}: {e}")

        logger.error(f"All data sources failed for {symbol}")
        return None

    def _fetch_from_yfinance(self, symbol: str, weeks: int) -> Optional[pd.DataFrame]:
        """Fetch data from yfinance."""
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)

        if data.empty:
            return None

        # Standardize column names
        data = data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Convert timezone-aware index to timezone-naive to prevent comparison issues
        if data.index.tz is not None:
            data.index = data.index.tz_convert(None)

        # Add ticker symbol
        data['symbol'] = symbol

        logger.debug(f"Fetched {len(data)} days of data for {symbol} from yfinance")
        return data

    def _fetch_from_alpha_vantage(self, symbol: str, weeks: int) -> Optional[pd.DataFrame]:
        """Fetch data from Alpha Vantage."""
        if not self.av_ts:
            return None

        # Rate limiting for Alpha Vantage (5 requests per minute)
        self._rate_limit_alpha_vantage()

        try:
            data, meta_data = self.av_ts.get_daily(symbol=symbol, outputsize='compact')

            if not data:
                return None

            # Convert to DataFrame
            df = pd.DataFrame.from_dict(data, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            # Standardize column names
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df = df.astype(float)

            # Filter to requested weeks
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=weeks)
            df = df[df.index >= start_date]

            # Add ticker symbol
            df['symbol'] = symbol

            logger.debug(f"Fetched {len(df)} days of data for {symbol} from Alpha Vantage")
            return df

        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            return None

    def _rate_limit_alpha_vantage(self):
        """Implement rate limiting for Alpha Vantage API (5 requests per minute)."""
        current_time = time.time()

        if current_time - self.last_request_time < 12:  # 12 seconds between requests
            sleep_time = 12 - (current_time - self.last_request_time)
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def fetch_multiple_stocks(self,
                            symbols: List[str],
                            weeks: int = 12,
                            max_workers: int = 10) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple stocks.

        Args:
            symbols: List of stock ticker symbols
            weeks: Number of weeks of historical data
            max_workers: Maximum concurrent requests (not used for rate-limited APIs)

        Returns:
            Dictionary mapping symbols to their DataFrames
        """
        results = {}
        failed_symbols = []

        for i, symbol in enumerate(symbols):
            logger.info(f"Fetching data for {symbol} ({i+1}/{len(symbols)})")

            data = self.fetch_stock_data(symbol, weeks)

            if data is not None:
                results[symbol] = data
            else:
                failed_symbols.append(symbol)

            # Progress update every 50 symbols
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(symbols)} symbols processed")

        if failed_symbols:
            logger.warning(f"Failed to fetch data for {len(failed_symbols)} symbols: {failed_symbols[:10]}...")

        logger.info(f"Successfully fetched data for {len(results)}/{len(symbols)} symbols")
        return results

    def validate_data_quality(self, data: pd.DataFrame, symbol: str) -> bool:
        """
        Validate the quality of fetched data.

        Args:
            data: Stock data DataFrame
            symbol: Stock ticker symbol

        Returns:
            True if data quality is acceptable
        """
        if data is None or data.empty:
            return False

        # Check for minimum data points (at least 30 trading days)
        if len(data) < 30:
            logger.warning(f"{symbol}: Insufficient data points ({len(data)})")
            return False

        # Check for missing values in essential columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"{symbol}: Missing column {col}")
                return False

            if data[col].isna().sum() > len(data) * 0.1:  # More than 10% missing
                logger.warning(f"{symbol}: Too many missing values in {col}")
                return False

        # Check for data integrity (high >= low, etc.)
        invalid_hlc = (data['high'] < data['low']).sum()
        if invalid_hlc > 0:
            logger.warning(f"{symbol}: {invalid_hlc} days with high < low")
            return False

        # Check for reasonable price ranges (no zero or negative prices)
        if (data[['open', 'high', 'low', 'close']] <= 0).any().any():
            logger.warning(f"{symbol}: Zero or negative prices detected")
            return False

        return True

    def get_data_summary(self, data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """Generate a summary of fetched data."""
        summary = {
            'total_symbols': len(data_dict),
            'date_range': {},
            'avg_data_points': 0,
            'symbols_with_gaps': []
        }

        if not data_dict:
            return summary

        all_data_points = []
        earliest_date = None
        latest_date = None

        for symbol, data in data_dict.items():
            data_points = len(data)
            all_data_points.append(data_points)

            # Check date range (ensure timezone-naive for comparison)
            symbol_earliest = data.index.min()
            symbol_latest = data.index.max()

            # Convert to timezone-naive if needed
            if hasattr(symbol_earliest, 'tz') and symbol_earliest.tz is not None:
                symbol_earliest = symbol_earliest.tz_convert(None)
            if hasattr(symbol_latest, 'tz') and symbol_latest.tz is not None:
                symbol_latest = symbol_latest.tz_convert(None)

            if earliest_date is None or symbol_earliest < earliest_date:
                earliest_date = symbol_earliest
            if latest_date is None or symbol_latest > latest_date:
                latest_date = symbol_latest

            # Check for significant gaps (more than 5 missing days in a row)
            data_sorted = data.sort_index()
            date_diffs = data_sorted.index.to_series().diff().dt.days
            max_gap = date_diffs.max()
            if max_gap > 5:
                summary['symbols_with_gaps'].append(symbol)

        summary['avg_data_points'] = np.mean(all_data_points) if all_data_points else 0
        summary['date_range'] = {
            'earliest': earliest_date,
            'latest': latest_date
        }

        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test the data fetcher
    fetcher = DataFetcher()

    # Test with a few symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    print("Testing data fetcher with sample symbols...")
    data_dict = fetcher.fetch_multiple_stocks(test_symbols, weeks=12)

    for symbol, data in data_dict.items():
        print(f"\n{symbol}: {len(data)} days of data")
        if not data.empty:
            print(f"  Date range: {data.index.min()} to {data.index.max()}")
            print(f"  Latest close: ${data['close'].iloc[-1]:.2f}")
            print(f"  Avg volume: {data['volume'].mean():,.0f}")

    summary = fetcher.get_data_summary(data_dict)
    print(f"\nData Summary: {summary}")