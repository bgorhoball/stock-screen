"""
Finnhub real-time monitoring module for VCP breakout detection.
"""

import requests
import pandas as pd
import numpy as np
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, NamedTuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BreakoutAlert(NamedTuple):
    """Breakout alert information."""
    symbol: str
    current_price: float
    resistance_level: float
    breakout_percentage: float
    current_volume: int
    avg_volume: int
    volume_ratio: float
    timestamp: datetime
    confidence: str


class FinnhubMonitor:
    """Real-time monitoring of VCP candidates using Finnhub API."""

    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            logger.warning("No Finnhub API key found. Real-time monitoring disabled.")

        self.base_url = "https://finnhub.io/api/v1"
        self.last_request_time = 0
        self.request_count = 0
        self.vcp_candidates = {}  # Store VCP resistance levels and metadata

    def add_vcp_candidate(self,
                         symbol: str,
                         resistance_level: float,
                         avg_volume: int,
                         confidence: float,
                         base_length_days: int) -> None:
        """
        Add a VCP candidate to real-time monitoring.

        Args:
            symbol: Stock ticker symbol
            resistance_level: VCP resistance/breakout level
            avg_volume: Average volume during VCP formation
            confidence: VCP detection confidence score
            base_length_days: Length of VCP base in days
        """
        self.vcp_candidates[symbol] = {
            'resistance_level': resistance_level,
            'avg_volume': avg_volume,
            'confidence': confidence,
            'base_length_days': base_length_days,
            'added_date': datetime.now(),
            'breakout_detected': False
        }
        logger.info(f"Added {symbol} to VCP monitoring: resistance=${resistance_level:.2f}, confidence={confidence:.2f}")

    def remove_vcp_candidate(self, symbol: str) -> None:
        """Remove a VCP candidate from monitoring."""
        if symbol in self.vcp_candidates:
            del self.vcp_candidates[symbol]
            logger.info(f"Removed {symbol} from VCP monitoring")

    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored VCP candidates."""
        return list(self.vcp_candidates.keys())

    def _rate_limit(self) -> None:
        """Implement rate limiting for Finnhub API (60 calls per minute)."""
        current_time = time.time()

        # 60 calls per minute = 1 call per second
        if current_time - self.last_request_time < 1.0:
            sleep_time = 1.0 - (current_time - self.last_request_time)
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request to Finnhub with rate limiting."""
        if not self.api_key:
            return None

        self._rate_limit()

        params['token'] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Finnhub API error for {endpoint}: {e}")
            return None

    def get_real_time_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with current price, volume, etc.
        """
        data = self._make_api_request("quote", {"symbol": symbol})

        if data and 'c' in data:  # 'c' is current price
            return {
                'symbol': symbol,
                'current_price': data['c'],
                'change': data.get('d', 0),
                'change_percent': data.get('dp', 0),
                'high': data.get('h', 0),
                'low': data.get('l', 0),
                'open': data.get('o', 0),
                'previous_close': data.get('pc', 0),
                'timestamp': datetime.now()
            }

        return None

    def get_volume_data(self, symbol: str, days: int = 20) -> Optional[Dict]:
        """
        Get recent volume data for volume analysis.

        Args:
            symbol: Stock ticker symbol
            days: Number of days of volume data

        Returns:
            Dictionary with volume statistics
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Format dates for Finnhub
        end_timestamp = int(end_date.timestamp())
        start_timestamp = int(start_date.timestamp())

        data = self._make_api_request("stock/candle", {
            "symbol": symbol,
            "resolution": "D",  # Daily data
            "from": start_timestamp,
            "to": end_timestamp
        })

        if data and data.get('s') == 'ok' and 'v' in data:
            volumes = data['v']
            if volumes:
                return {
                    'symbol': symbol,
                    'avg_volume': np.mean(volumes),
                    'latest_volume': volumes[-1] if volumes else 0,
                    'volume_trend': 'increasing' if len(volumes) > 1 and volumes[-1] > np.mean(volumes[:-1]) else 'stable',
                    'data_points': len(volumes)
                }

        return None

    def check_breakout(self, symbol: str) -> Optional[BreakoutAlert]:
        """
        Check if a VCP candidate has broken out.

        Args:
            symbol: Stock ticker symbol

        Returns:
            BreakoutAlert if breakout detected, None otherwise
        """
        if symbol not in self.vcp_candidates:
            return None

        candidate = self.vcp_candidates[symbol]

        # Skip if already detected breakout
        if candidate['breakout_detected']:
            return None

        # Get current quote
        quote = self.get_real_time_quote(symbol)
        if not quote:
            return None

        current_price = quote['current_price']
        resistance_level = candidate['resistance_level']

        # Check if price has broken above resistance
        if current_price <= resistance_level:
            return None

        # Calculate breakout percentage
        breakout_percentage = ((current_price - resistance_level) / resistance_level) * 100

        # Get volume data for confirmation
        volume_data = self.get_volume_data(symbol, days=20)

        if volume_data:
            current_volume = volume_data['latest_volume']
            avg_volume = volume_data['avg_volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        else:
            # Fallback to stored average
            current_volume = 0
            avg_volume = candidate['avg_volume']
            volume_ratio = 0

        # Determine confidence level
        confidence = "high" if volume_ratio > 1.5 and breakout_percentage > 1.0 else \
                    "medium" if volume_ratio > 1.0 or breakout_percentage > 0.5 else \
                    "low"

        # Mark as detected to avoid duplicate alerts
        candidate['breakout_detected'] = True

        alert = BreakoutAlert(
            symbol=symbol,
            current_price=current_price,
            resistance_level=resistance_level,
            breakout_percentage=breakout_percentage,
            current_volume=current_volume,
            avg_volume=int(avg_volume),
            volume_ratio=volume_ratio,
            timestamp=datetime.now(),
            confidence=confidence
        )

        logger.info(f"Breakout detected: {symbol} at ${current_price:.2f} "
                   f"(+{breakout_percentage:.1f}%) with {confidence} confidence")

        return alert

    def scan_all_candidates(self) -> List[BreakoutAlert]:
        """
        Scan all VCP candidates for breakouts.

        Returns:
            List of breakout alerts
        """
        alerts = []

        if not self.vcp_candidates:
            logger.debug("No VCP candidates to monitor")
            return alerts

        logger.info(f"Scanning {len(self.vcp_candidates)} VCP candidates for breakouts...")

        for symbol in list(self.vcp_candidates.keys()):
            try:
                alert = self.check_breakout(symbol)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"Error checking breakout for {symbol}: {e}")

        if alerts:
            logger.info(f"Found {len(alerts)} breakout alerts")
        else:
            logger.debug("No breakouts detected in current scan")

        return alerts

    def get_market_status(self) -> Dict:
        """
        Get current market status.

        Returns:
            Dictionary with market open/close status
        """
        data = self._make_api_request("stock/market-status", {"exchange": "US"})

        if data:
            return {
                'is_open': data.get('isOpen', False),
                'session': data.get('session', 'unknown'),
                'timezone': data.get('timezone', 'America/New_York'),
                'timestamp': datetime.now()
            }

        # Fallback: basic market hours check (9:30 AM - 4:00 PM ET)
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return {
            'is_open': market_open <= now <= market_close and now.weekday() < 5,
            'session': 'regular' if market_open <= now <= market_close else 'closed',
            'timezone': 'America/New_York',
            'timestamp': now
        }

    def cleanup_old_candidates(self, max_age_days: int = 14) -> None:
        """
        Remove VCP candidates older than specified days.

        Args:
            max_age_days: Maximum age in days before removal
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        old_symbols = []

        for symbol, candidate in self.vcp_candidates.items():
            if candidate['added_date'] < cutoff_date:
                old_symbols.append(symbol)

        for symbol in old_symbols:
            self.remove_vcp_candidate(symbol)

        if old_symbols:
            logger.info(f"Cleaned up {len(old_symbols)} old VCP candidates")

    def get_monitoring_summary(self) -> Dict:
        """Get summary of current monitoring status."""
        total_candidates = len(self.vcp_candidates)
        breakouts_detected = sum(1 for c in self.vcp_candidates.values() if c['breakout_detected'])

        avg_confidence = np.mean([c['confidence'] for c in self.vcp_candidates.values()]) if self.vcp_candidates else 0

        return {
            'total_candidates': total_candidates,
            'active_monitoring': total_candidates - breakouts_detected,
            'breakouts_detected': breakouts_detected,
            'avg_confidence': avg_confidence,
            'api_calls_made': self.request_count,
            'last_scan': datetime.now()
        }


if __name__ == "__main__":
    # Test the Finnhub monitor
    logging.basicConfig(level=logging.INFO)

    monitor = FinnhubMonitor()

    # Test with sample VCP candidates
    monitor.add_vcp_candidate("AAPL", 175.0, 50000000, 0.85, 42)
    monitor.add_vcp_candidate("MSFT", 380.0, 25000000, 0.72, 28)

    print(f"Monitoring {len(monitor.get_monitored_symbols())} VCP candidates")

    # Test market status
    market_status = monitor.get_market_status()
    print(f"Market status: {market_status}")

    # Test real-time quotes
    for symbol in monitor.get_monitored_symbols():
        quote = monitor.get_real_time_quote(symbol)
        if quote:
            print(f"{symbol}: ${quote['current_price']:.2f} ({quote['change_percent']:+.2f}%)")

    # Test breakout scanning
    alerts = monitor.scan_all_candidates()
    print(f"Breakout alerts: {len(alerts)}")

    for alert in alerts:
        print(f"🚀 {alert.symbol} breakout: ${alert.current_price:.2f} "
              f"(+{alert.breakout_percentage:.1f}%) - {alert.confidence} confidence")

    # Show monitoring summary
    summary = monitor.get_monitoring_summary()
    print(f"Monitoring summary: {summary}")