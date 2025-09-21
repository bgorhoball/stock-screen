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
        # Expanded static fallback list with more S&P 500 stocks for robust testing
        self.static_fallback = [
            # Mega Cap Technology
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
            'AVGO', 'ORCL', 'CRM', 'ADBE', 'AMD', 'QCOM', 'INTC', 'NOW',
            'INTU', 'CSCO', 'TXN', 'IBM', 'AMAT', 'MU', 'ADI', 'KLAC',
            'LRCX', 'NXPI', 'MCHP', 'SNPS', 'CDNS', 'FTNT', 'ANET', 'PANW',

            # Healthcare & Pharmaceuticals
            'UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'LLY', 'DHR',
            'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN', 'ZTS', 'BIIB', 'ISRG',
            'CVS', 'CI', 'HUM', 'ANTM', 'BSX', 'MDT', 'SYK', 'EW', 'BDX',
            'A', 'IQV', 'RMD', 'IDXX', 'ALGN', 'MRNA', 'ILMN', 'DXCM',

            # Financials
            'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP',
            'BLK', 'SCHW', 'SPGI', 'MMC', 'ICE', 'CME', 'AON', 'COF', 'USB',
            'TFC', 'PNC', 'BK', 'AIG', 'MET', 'PRU', 'ALL', 'TRV', 'CB',

            # Consumer & Retail
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'NKE', 'DIS', 'MCD',
            'SBUX', 'TJX', 'LOW', 'TGT', 'BKNG', 'CL', 'KMB', 'GIS', 'K',
            'MO', 'MDLZ', 'HSY', 'STZ', 'EL', 'PVH', 'RL', 'LULU', 'ULTA',

            # Energy & Utilities
            'CVX', 'XOM', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'OXY',
            'KMI', 'WMB', 'NEE', 'SO', 'DUK', 'AEP', 'EXC', 'XEL', 'PCG',

            # Industrials & Materials
            'UNP', 'RTX', 'HON', 'UPS', 'LMT', 'BA', 'CAT', 'DE', 'MMM',
            'GE', 'EMR', 'ETN', 'ITW', 'JCI', 'FDX', 'NSC', 'CSX', 'WM',
            'GD', 'NOC', 'LHX', 'CARR', 'OTIS', 'RSG', 'IR', 'PCAR', 'PH',

            # Communication & Media
            'T', 'VZ', 'CMCSA', 'NFLX', 'CHTR', 'TMUS', 'DISH', 'VIA', 'FOXA',

            # REITs & Real Estate
            'PLD', 'EQIX', 'PSA', 'EQR', 'WELL', 'DLR', 'SPG', 'O', 'CCI',

            # Other Major S&P 500 Components
            'ACN', 'FI', 'APD', 'LIN', 'ECL', 'SHW', 'PPG', 'DD', 'DOW',
            'COIN', 'PYPL', 'EBAY', 'SHOP', 'SQ', 'ROKU', 'ZM', 'DOCU'
        ]

    def get_sp500_tickers(self) -> List[str]:
        """
        Fetch S&P 500 tickers with multiple fallback methods.

        Returns:
            List of S&P 500 ticker symbols
        """
        # Try Wikipedia first
        try:
            tickers = self._fetch_from_wikipedia()
            if len(tickers) >= 400:  # Wikipedia should have 500+ tickers
                return tickers
            else:
                logger.warning(f"Wikipedia returned only {len(tickers)} tickers, trying fallback methods")
        except Exception as e:
            logger.warning(f"Wikipedia fetch failed: {e}")

        # Try yfinance fallback
        try:
            tickers = self._fetch_from_yfinance()
            if len(tickers) >= 400:
                return tickers
            else:
                logger.warning(f"yfinance returned only {len(tickers)} tickers, using static fallback")
        except Exception as e:
            logger.warning(f"yfinance fetch failed: {e}")

        # Use static fallback
        logger.info(f"Using static fallback list with {len(self.static_fallback)} tickers")
        return self.static_fallback

    def _fetch_from_wikipedia(self) -> List[str]:
        """Fetch S&P 500 tickers from Wikipedia."""
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        try:
            logger.info("Attempting to fetch S&P 500 tickers from Wikipedia...")
            tables = pd.read_html(url)

            if not tables:
                raise ValueError("No tables found on Wikipedia page")

            sp500_table = tables[0]

            if 'Symbol' not in sp500_table.columns:
                # Try alternative column names
                possible_columns = ['Ticker', 'Ticker symbol', 'Symbol', 'Stock Symbol']
                symbol_col = None
                for col in possible_columns:
                    if col in sp500_table.columns:
                        symbol_col = col
                        break

                if symbol_col is None:
                    raise ValueError(f"Symbol column not found. Available columns: {list(sp500_table.columns)}")

                logger.info(f"Using '{symbol_col}' column for ticker symbols")
                tickers = sp500_table[symbol_col].tolist()
            else:
                tickers = sp500_table['Symbol'].tolist()

            # Clean up ticker symbols (replace dots with dashes for yfinance compatibility)
            tickers = [str(ticker).replace('.', '-').strip() for ticker in tickers if pd.notna(ticker)]

            # Remove any empty or invalid tickers
            tickers = [ticker for ticker in tickers if ticker and len(ticker) >= 1 and len(ticker) <= 10]

            logger.info(f"Successfully fetched {len(tickers)} tickers from Wikipedia")

            if len(tickers) < 400:
                logger.warning(f"Only {len(tickers)} tickers fetched from Wikipedia. Expected 400+. May indicate parsing issues.")

            return tickers

        except Exception as e:
            logger.error(f"Failed to fetch from Wikipedia: {e}")
            logger.info("This could be due to missing dependencies (lxml, html5lib) or network issues")
            raise

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