"""
S&P 500 ticker fetching module with fallback options.
"""

import requests
import pandas as pd
import yfinance as yf
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class SP500TickerFetcher:
    """Fetches S&P 500 ticker symbols from multiple sources with fallbacks."""

    def __init__(self):
        self.static_fallback = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B',
            'UNH', 'JNJ', 'V', 'WMT', 'JPM', 'MA', 'PG', 'HD', 'CVX', 'ABBV',
            'BAC', 'ORCL', 'KO', 'AVGO', 'PEP', 'COST', 'TMO', 'MRK', 'LLY',
            'ACN', 'NFLX', 'ADBE', 'NKE', 'DHR', 'TXN', 'DIS', 'VZ', 'ABT',
            'CRM', 'QCOM', 'AMD', 'PM', 'INTC', 'NEE', 'RTX', 'WFC', 'BMY',
            'CMCSA', 'T', 'UNP', 'LOW', 'HON', 'IBM', 'LIN', 'SPGI', 'COP',
            'UPS', 'MDT', 'GS', 'ELV', 'BLK', 'GILD', 'C', 'CAT', 'ISRG',
            'AXP', 'DE', 'PLD', 'MMM', 'BA', 'BKNG', 'ADP', 'TJX', 'SYK',
            'MO', 'MDLZ', 'ZTS', 'AMGN', 'CVS', 'GE', 'CI', 'VRTX', 'NOW',
            'SO', 'SCHW', 'REGN', 'LMT', 'PFE', 'ADI', 'SLB', 'TMUS', 'DUK',
            'FI', 'MU', 'BSX', 'EOG', 'CSX', 'EQIX', 'ETN', 'ITW', 'NSC',
            'AON', 'WM', 'FCX', 'PSA', 'CL', 'USB', 'KLAC', 'APD', 'LRCX',
            'GD', 'ICE', 'SHW', 'PNC', 'HUM', 'FDX', 'F', 'ECL', 'CME',
            'EMR', 'TFC', 'NXPI', 'DG', 'ANET', 'GM', 'AIG', 'DXCM', 'TGT',
            'JCI', 'HCA', 'BDX', 'PCAR', 'BIIB', 'KMB', 'PYPL', 'COIN'
        ]

    def get_sp500_tickers(self) -> List[str]:
        """
        Fetch S&P 500 tickers with multiple fallback methods.

        Returns:
            List of S&P 500 ticker symbols
        """
        try:
            return self._fetch_from_wikipedia()
        except Exception as e:
            logger.warning(f"Wikipedia fetch failed: {e}")
            try:
                return self._fetch_from_yfinance()
            except Exception as e:
                logger.warning(f"yfinance fetch failed: {e}")
                logger.info("Using static fallback list")
                return self.static_fallback

    def _fetch_from_wikipedia(self) -> List[str]:
        """Fetch S&P 500 tickers from Wikipedia."""
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()

        # Clean up ticker symbols (replace dots with dashes for yfinance compatibility)
        tickers = [ticker.replace('.', '-') for ticker in tickers]

        logger.info(f"Fetched {len(tickers)} tickers from Wikipedia")
        return tickers

    def _fetch_from_yfinance(self) -> List[str]:
        """Fetch S&P 500 tickers using yfinance."""
        sp500 = yf.Ticker("^GSPC")
        # This is a simplified approach - in practice, yfinance doesn't directly provide constituents
        # We'll use our static list as the fallback
        logger.info("yfinance fallback - using static list")
        return self.static_fallback

    def save_tickers_to_file(self, tickers: List[str], filename: str = "s&p500_tickers.txt") -> None:
        """Save tickers to a text file."""
        with open(filename, 'w') as f:
            for ticker in tickers:
                f.write(f"{ticker}\n")
        logger.info(f"Saved {len(tickers)} tickers to {filename}")

    def load_tickers_from_file(self, filename: str = "s&p500_tickers.txt") -> List[str]:
        """Load tickers from a text file."""
        try:
            with open(filename, 'r') as f:
                tickers = [line.strip() for line in f.readlines()]
            logger.info(f"Loaded {len(tickers)} tickers from {filename}")
            return tickers
        except FileNotFoundError:
            logger.warning(f"File {filename} not found, fetching fresh tickers")
            return self.get_sp500_tickers()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = SP500TickerFetcher()
    tickers = fetcher.get_sp500_tickers()

    print(f"Found {len(tickers)} S&P 500 tickers")
    print(f"First 10: {tickers[:10]}")

    # Save to file
    fetcher.save_tickers_to_file(tickers)