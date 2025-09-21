"""
Volatility Contraction Pattern (VCP) detection algorithm
based on Mark Minervini's methodology.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
import logging

logger = logging.getLogger(__name__)

class VCPResult(NamedTuple):
    """Result of VCP pattern detection."""
    detected: bool
    confidence: float
    contractions: List[Dict]
    breakout_date: Optional[datetime]
    breakout_price: Optional[float]
    base_length_days: int
    volume_trend: str
    notes: List[str]


class VCPDetector:
    """Detects Volatility Contraction Pattern in stock price data."""

    def __init__(self, config: Dict = None):
        """
        Initialize VCP detector with configuration.

        Args:
            config: Configuration dictionary with VCP parameters
        """
        default_config = {
            'min_contractions': 2,
            'max_contractions': 6,
            'min_base_length_days': 7,
            'volume_decrease_threshold': 0.8,
            'max_pullback_percentage': 50.0,
            'breakout_volume_multiplier': 1.5,
            'price_near_highs_threshold': 0.75,  # Within 25% of 52-week high
            'min_price': 10.0,
            'min_average_volume': 100000
        }

        self.config = {**default_config, **(config or {})}

    def detect_vcp(self, data: pd.DataFrame, symbol: str) -> VCPResult:
        """
        Main VCP detection method.

        Args:
            data: Stock price DataFrame with OHLCV data
            symbol: Stock ticker symbol

        Returns:
            VCPResult with detection results
        """
        if not self._validate_input_data(data):
            return VCPResult(
                detected=False,
                confidence=0.0,
                contractions=[],
                breakout_date=None,
                breakout_price=None,
                base_length_days=0,
                volume_trend="insufficient_data",
                notes=["Insufficient or invalid data"]
            )

        try:
            # Step 1: Check basic requirements
            if not self._meets_basic_requirements(data):
                return VCPResult(
                    detected=False,
                    confidence=0.0,
                    contractions=[],
                    breakout_date=None,
                    breakout_price=None,
                    base_length_days=0,
                    volume_trend="failed_basic_requirements",
                    notes=["Failed basic price/volume requirements"]
                )

            # Step 2: Identify potential pivot points (local highs and lows)
            pivots = self._identify_pivot_points(data)

            # Step 3: Find contraction sequences
            contractions = self._find_contractions(data, pivots)

            if len(contractions) < self.config['min_contractions']:
                return VCPResult(
                    detected=False,
                    confidence=0.0,
                    contractions=contractions,
                    breakout_date=None,
                    breakout_price=None,
                    base_length_days=0,
                    volume_trend="insufficient_contractions",
                    notes=[f"Only {len(contractions)} contractions found, minimum {self.config['min_contractions']} required"]
                )

            # Step 4: Validate contraction pattern
            is_valid_pattern = self._validate_contraction_pattern(contractions)

            # Step 5: Check volume behavior
            volume_trend = self._analyze_volume_trend(data, contractions)

            # Step 6: Check if price is near highs
            near_highs = self._is_price_near_highs(data)

            # Step 7: Look for breakout
            breakout_info = self._detect_breakout(data, contractions)

            # Step 8: Calculate confidence score
            confidence = self._calculate_confidence_score(
                contractions, volume_trend, near_highs, breakout_info, data
            )

            # Step 9: Calculate base length
            base_length = self._calculate_base_length(contractions)

            # Generate notes
            notes = self._generate_notes(
                contractions, volume_trend, near_highs, breakout_info, confidence
            )

            detected = (
                is_valid_pattern and
                confidence >= 0.5 and
                len(contractions) >= self.config['min_contractions']
            )

            return VCPResult(
                detected=detected,
                confidence=confidence,
                contractions=contractions,
                breakout_date=breakout_info.get('date'),
                breakout_price=breakout_info.get('price'),
                base_length_days=base_length,
                volume_trend=volume_trend,
                notes=notes
            )

        except Exception as e:
            logger.error(f"Error detecting VCP for {symbol}: {e}")
            return VCPResult(
                detected=False,
                confidence=0.0,
                contractions=[],
                breakout_date=None,
                breakout_price=None,
                base_length_days=0,
                volume_trend="error",
                notes=[f"Error in detection: {str(e)}"]
            )

    def _validate_input_data(self, data: pd.DataFrame) -> bool:
        """Validate input data quality."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']

        if data is None or data.empty:
            return False

        for col in required_columns:
            if col not in data.columns:
                return False

        # Need at least 30 trading days
        if len(data) < 30:
            return False

        return True

    def _meets_basic_requirements(self, data: pd.DataFrame) -> bool:
        """Check if stock meets basic screening requirements."""
        latest_price = data['close'].iloc[-1]
        avg_volume = data['volume'].mean()

        return (
            latest_price >= self.config['min_price'] and
            avg_volume >= self.config['min_average_volume']
        )

    def _identify_pivot_points(self, data: pd.DataFrame, window: int = 5) -> Dict[str, List]:
        """
        Identify pivot highs and lows.

        Args:
            data: Price data
            window: Window size for pivot detection

        Returns:
            Dictionary with 'highs' and 'lows' lists
        """
        highs = []
        lows = []

        for i in range(window, len(data) - window):
            # Check for pivot high
            if all(data['high'].iloc[i] >= data['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(data['high'].iloc[i] >= data['high'].iloc[i+j] for j in range(1, window+1)):
                highs.append({
                    'date': data.index[i],
                    'price': data['high'].iloc[i],
                    'index': i
                })

            # Check for pivot low
            if all(data['low'].iloc[i] <= data['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(data['low'].iloc[i] <= data['low'].iloc[i+j] for j in range(1, window+1)):
                lows.append({
                    'date': data.index[i],
                    'price': data['low'].iloc[i],
                    'index': i
                })

        return {'highs': highs, 'lows': lows}

    def _find_contractions(self, data: pd.DataFrame, pivots: Dict) -> List[Dict]:
        """
        Find contraction sequences in the price data.

        Args:
            data: Price data
            pivots: Pivot points dictionary

        Returns:
            List of contraction dictionaries
        """
        contractions = []
        highs = pivots['highs']

        if len(highs) < 2:
            return contractions

        # Look for sequences of declining pullbacks from highs
        for i in range(len(highs) - 1):
            current_high = highs[i]
            next_high = highs[i + 1]

            # Find the low between these highs
            start_idx = current_high['index']
            end_idx = next_high['index']

            if end_idx - start_idx < 3:  # Too short to be meaningful
                continue

            # Find the lowest point between the highs
            segment = data.iloc[start_idx:end_idx+1]
            low_idx = segment['low'].idxmin()
            low_price = segment.loc[low_idx, 'low']

            # Calculate pullback percentage
            pullback_pct = ((current_high['price'] - low_price) / current_high['price']) * 100

            # Calculate average volume during contraction
            avg_volume = segment['volume'].mean()

            contraction = {
                'start_date': current_high['date'],
                'end_date': next_high['date'],
                'start_price': current_high['price'],
                'end_price': next_high['price'],
                'low_price': low_price,
                'low_date': low_idx,
                'pullback_percentage': pullback_pct,
                'duration_days': (next_high['date'] - current_high['date']).days,
                'avg_volume': avg_volume,
                'price_range': current_high['price'] - low_price
            }

            contractions.append(contraction)

        return contractions

    def _validate_contraction_pattern(self, contractions: List[Dict]) -> bool:
        """
        Validate that contractions follow the VCP pattern.

        Args:
            contractions: List of contraction dictionaries

        Returns:
            True if pattern is valid
        """
        if len(contractions) < self.config['min_contractions']:
            return False

        # Check that pullbacks are generally decreasing
        pullbacks = [c['pullback_percentage'] for c in contractions]

        # Allow some variation, but general trend should be decreasing
        decreasing_count = 0
        for i in range(1, len(pullbacks)):
            if pullbacks[i] <= pullbacks[i-1] * 1.2:  # Allow 20% tolerance
                decreasing_count += 1

        # At least 70% of contractions should follow the pattern
        required_decreasing = max(1, int(len(pullbacks) * 0.7))

        return decreasing_count >= required_decreasing

    def _analyze_volume_trend(self, data: pd.DataFrame, contractions: List[Dict]) -> str:
        """
        Analyze volume trend during contractions.

        Args:
            data: Price data
            contractions: List of contractions

        Returns:
            Volume trend description
        """
        if not contractions:
            return "no_contractions"

        volume_trends = []

        for contraction in contractions:
            # Compare volume during contraction with previous period
            start_idx = data.index.get_loc(contraction['start_date'])
            end_idx = data.index.get_loc(contraction['end_date'])

            contraction_volume = data.iloc[start_idx:end_idx+1]['volume'].mean()

            # Compare with volume before contraction (same period length)
            period_length = end_idx - start_idx + 1
            prev_start = max(0, start_idx - period_length)
            prev_volume = data.iloc[prev_start:start_idx]['volume'].mean()

            if prev_volume > 0:
                volume_ratio = contraction_volume / prev_volume
                volume_trends.append(volume_ratio)

        if not volume_trends:
            return "insufficient_data"

        avg_volume_ratio = np.mean(volume_trends)

        if avg_volume_ratio < self.config['volume_decrease_threshold']:
            return "decreasing"
        elif avg_volume_ratio > 1.2:
            return "increasing"
        else:
            return "stable"

    def _is_price_near_highs(self, data: pd.DataFrame) -> bool:
        """Check if current price is near recent highs."""
        current_price = data['close'].iloc[-1]
        recent_high = data['high'].iloc[-60:].max()  # 60-day high

        return current_price >= recent_high * self.config['price_near_highs_threshold']

    def _detect_breakout(self, data: pd.DataFrame, contractions: List[Dict]) -> Dict:
        """
        Detect potential breakout from the VCP pattern.

        Args:
            data: Price data
            contractions: List of contractions

        Returns:
            Breakout information dictionary
        """
        if not contractions:
            return {}

        # Find the highest point of the most recent contraction
        last_contraction = contractions[-1]
        resistance_level = last_contraction['start_price']

        # Look for breakout in recent data (last 10 days)
        recent_data = data.iloc[-10:]

        for i, (date, row) in enumerate(recent_data.iterrows()):
            if row['close'] > resistance_level:
                # Check volume confirmation
                avg_volume = data['volume'].iloc[-20:-10].mean()  # Previous 10 days average
                breakout_volume = row['volume']

                volume_confirmed = breakout_volume > avg_volume * self.config['breakout_volume_multiplier']

                return {
                    'detected': True,
                    'date': date,
                    'price': row['close'],
                    'resistance_level': resistance_level,
                    'volume_confirmed': volume_confirmed,
                    'volume_ratio': breakout_volume / avg_volume if avg_volume > 0 else 0
                }

        return {'detected': False}

    def _calculate_confidence_score(self,
                                  contractions: List[Dict],
                                  volume_trend: str,
                                  near_highs: bool,
                                  breakout_info: Dict,
                                  data: pd.DataFrame) -> float:
        """Calculate confidence score for VCP detection."""
        score = 0.0

        # Base score for having contractions
        if len(contractions) >= self.config['min_contractions']:
            score += 0.3

        # Additional points for more contractions (up to optimal number)
        optimal_contractions = 3
        if len(contractions) >= optimal_contractions:
            score += 0.1

        # Volume trend scoring
        if volume_trend == "decreasing":
            score += 0.25
        elif volume_trend == "stable":
            score += 0.1

        # Price near highs
        if near_highs:
            score += 0.15

        # Breakout detection
        if breakout_info.get('detected', False):
            score += 0.15
            if breakout_info.get('volume_confirmed', False):
                score += 0.1

        # Pattern quality (decreasing pullbacks)
        if len(contractions) >= 2:
            pullbacks = [c['pullback_percentage'] for c in contractions]
            if all(pullbacks[i] <= pullbacks[i-1] * 1.1 for i in range(1, len(pullbacks))):
                score += 0.1

        return min(1.0, score)

    def _calculate_base_length(self, contractions: List[Dict]) -> int:
        """Calculate the total length of the base in days."""
        if not contractions:
            return 0

        start_date = contractions[0]['start_date']
        end_date = contractions[-1]['end_date']

        return (end_date - start_date).days

    def _generate_notes(self,
                       contractions: List[Dict],
                       volume_trend: str,
                       near_highs: bool,
                       breakout_info: Dict,
                       confidence: float) -> List[str]:
        """Generate descriptive notes for the VCP detection."""
        notes = []

        notes.append(f"{len(contractions)} contractions detected")

        if contractions:
            pullbacks = [c['pullback_percentage'] for c in contractions]
            notes.append(f"Pullback range: {min(pullbacks):.1f}% - {max(pullbacks):.1f}%")

        notes.append(f"Volume trend: {volume_trend}")

        if near_highs:
            notes.append("Price near recent highs")

        if breakout_info.get('detected', False):
            if breakout_info.get('volume_confirmed', False):
                notes.append("Breakout detected with volume confirmation")
            else:
                notes.append("Breakout detected without volume confirmation")

        notes.append(f"Confidence: {confidence:.2f}")

        return notes


if __name__ == "__main__":
    # Test the VCP detector
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)

    detector = VCPDetector()

    # Test with a sample stock
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period="6mo")

    data = data.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })

    result = detector.detect_vcp(data, "AAPL")

    print(f"VCP Detected: {result.detected}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Contractions: {len(result.contractions)}")
    print(f"Volume Trend: {result.volume_trend}")
    print(f"Notes: {result.notes}")

    if result.breakout_date:
        print(f"Breakout: {result.breakout_date} at ${result.breakout_price:.2f}")