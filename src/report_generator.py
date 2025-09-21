"""
Report generation module for VCP screening results.
"""

import pandas as pd
import csv
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates reports from VCP screening results."""

    def __init__(self, output_dir: str = "daily_reports"):
        """
        Initialize report generator.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_csv_report(self,
                          vcp_results: Dict,
                          filename: Optional[str] = None) -> str:
        """
        Generate CSV report from VCP screening results.

        Args:
            vcp_results: Dictionary mapping symbols to VCP results
            filename: Optional custom filename

        Returns:
            Path to generated report file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vcp_matches_{timestamp}.csv"

        filepath = os.path.join(self.output_dir, filename)

        # Filter for detected VCP patterns
        detected_vcps = {
            symbol: result for symbol, result in vcp_results.items()
            if result.detected
        }

        if not detected_vcps:
            logger.info("No VCP patterns detected - creating empty report")
            # Create empty report with headers
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'symbol', 'confidence', 'contractions_count', 'base_length_days',
                    'volume_trend', 'breakout_detected', 'breakout_date', 'breakout_price',
                    'pullback_range_min', 'pullback_range_max', 'notes'
                ])
            return filepath

        # Prepare data for CSV
        csv_data = []
        for symbol, result in detected_vcps.items():
            # Calculate pullback range
            pullbacks = [c['pullback_percentage'] for c in result.contractions]
            pullback_min = min(pullbacks) if pullbacks else 0
            pullback_max = max(pullbacks) if pullbacks else 0

            row = {
                'symbol': symbol,
                'confidence': round(result.confidence, 3),
                'contractions_count': len(result.contractions),
                'base_length_days': result.base_length_days,
                'volume_trend': result.volume_trend,
                'breakout_detected': result.breakout_date is not None,
                'breakout_date': result.breakout_date.strftime('%Y-%m-%d') if result.breakout_date else '',
                'breakout_price': round(result.breakout_price, 2) if result.breakout_price else '',
                'pullback_range_min': round(pullback_min, 1),
                'pullback_range_max': round(pullback_max, 1),
                'notes': '; '.join(result.notes)
            }
            csv_data.append(row)

        # Sort by confidence score (highest first)
        csv_data.sort(key=lambda x: x['confidence'], reverse=True)

        # Write to CSV
        df = pd.DataFrame(csv_data)
        df.to_csv(filepath, index=False)

        logger.info(f"Generated CSV report: {filepath} with {len(csv_data)} VCP matches")
        return filepath

    def generate_summary_report(self,
                              vcp_results: Dict,
                              data_summary: Dict,
                              execution_time: float) -> Dict:
        """
        Generate summary statistics from screening results.

        Args:
            vcp_results: Dictionary mapping symbols to VCP results
            data_summary: Data fetching summary
            execution_time: Total execution time in seconds

        Returns:
            Summary dictionary
        """
        total_symbols = len(vcp_results)
        detected_vcps = sum(1 for result in vcp_results.values() if result.detected)

        # Confidence distribution
        confidence_scores = [result.confidence for result in vcp_results.values()]
        high_confidence = sum(1 for score in confidence_scores if score >= 0.8)
        medium_confidence = sum(1 for score in confidence_scores if 0.5 <= score < 0.8)

        # Volume trend analysis
        volume_trends = {}
        for result in vcp_results.values():
            trend = result.volume_trend
            volume_trends[trend] = volume_trends.get(trend, 0) + 1

        # Breakout analysis
        breakouts_detected = sum(1 for result in vcp_results.values()
                               if result.breakout_date is not None)

        summary = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'execution_time_seconds': round(execution_time, 2),
            'total_symbols_scanned': total_symbols,
            'symbols_with_data': data_summary.get('total_symbols', 0),
            'vcp_patterns_detected': detected_vcps,
            'vcp_detection_rate': round(detected_vcps / total_symbols * 100, 2) if total_symbols > 0 else 0,
            'high_confidence_matches': high_confidence,
            'medium_confidence_matches': medium_confidence,
            'breakouts_detected': breakouts_detected,
            'volume_trend_distribution': volume_trends,
            'avg_data_points_per_symbol': round(data_summary.get('avg_data_points', 0), 1),
            'data_date_range': {
                'earliest': data_summary.get('date_range', {}).get('earliest'),
                'latest': data_summary.get('date_range', {}).get('latest')
            }
        }

        return summary

    def save_summary_json(self, summary: Dict, filename: Optional[str] = None) -> str:
        """
        Save summary report as JSON file.

        Args:
            summary: Summary dictionary
            filename: Optional custom filename

        Returns:
            Path to saved JSON file
        """
        import json

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vcp_summary_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)

        # Convert datetime objects to strings for JSON serialization
        json_summary = summary.copy()
        date_range = json_summary.get('data_date_range', {})
        if date_range.get('earliest'):
            date_range['earliest'] = date_range['earliest'].strftime('%Y-%m-%d')
        if date_range.get('latest'):
            date_range['latest'] = date_range['latest'].strftime('%Y-%m-%d')

        with open(filepath, 'w') as f:
            json.dump(json_summary, f, indent=2)

        logger.info(f"Generated summary JSON: {filepath}")
        return filepath

    def print_summary_to_console(self, summary: Dict) -> None:
        """Print summary report to console."""
        print("\n" + "="*60)
        print("VCP SCREENING SUMMARY REPORT")
        print("="*60)
        print(f"Scan Date: {summary['scan_date']}")
        print(f"Execution Time: {summary['execution_time_seconds']} seconds")
        print()
        print("SCANNING RESULTS:")
        print(f"  Total symbols processed: {summary['total_symbols_scanned']}")
        print(f"  Symbols with valid data: {summary['symbols_with_data']}")
        print(f"  VCP patterns detected: {summary['vcp_patterns_detected']}")
        print(f"  Detection rate: {summary['vcp_detection_rate']}%")
        print()
        print("CONFIDENCE BREAKDOWN:")
        print(f"  High confidence (≥0.8): {summary['high_confidence_matches']}")
        print(f"  Medium confidence (0.5-0.8): {summary['medium_confidence_matches']}")
        print()
        print("PATTERN ANALYSIS:")
        print(f"  Breakouts detected: {summary['breakouts_detected']}")
        print("  Volume trends:")
        for trend, count in summary['volume_trend_distribution'].items():
            print(f"    {trend}: {count}")
        print()
        print("DATA QUALITY:")
        print(f"  Avg data points per symbol: {summary['avg_data_points_per_symbol']}")

        date_range = summary['data_date_range']
        if date_range.get('earliest') and date_range.get('latest'):
            print(f"  Date range: {date_range['earliest']} to {date_range['latest']}")

        print("="*60)

    def create_github_issue_content(self,
                                   summary: Dict,
                                   top_matches: List[Dict],
                                   max_matches: int = 10) -> str:
        """
        Create formatted content for GitHub issue report.

        Args:
            summary: Summary statistics
            top_matches: List of top VCP matches
            max_matches: Maximum number of matches to include

        Returns:
            Formatted markdown content
        """
        content = f"""# Daily VCP Screening Report - {summary['scan_date'].split()[0]}

## 📊 Summary
- **Total symbols scanned:** {summary['total_symbols_scanned']}
- **VCP patterns detected:** {summary['vcp_patterns_detected']}
- **Detection rate:** {summary['vcp_detection_rate']}%
- **Execution time:** {summary['execution_time_seconds']} seconds

## 🎯 High-Confidence Matches

"""

        if not top_matches:
            content += "*No VCP patterns detected today.*\n"
        else:
            content += "| Symbol | Confidence | Contractions | Base Days | Volume Trend | Breakout |\n"
            content += "|--------|------------|--------------|-----------|--------------|----------|\n"

            for match in top_matches[:max_matches]:
                breakout = "✅" if match.get('breakout_detected', False) else "⏳"
                content += f"| {match['symbol']} | {match['confidence']:.2f} | {match['contractions_count']} | {match['base_length_days']} | {match['volume_trend']} | {breakout} |\n"

        content += f"""

## 📈 Pattern Analysis
- **High confidence (≥0.8):** {summary['high_confidence_matches']}
- **Medium confidence (0.5-0.8):** {summary['medium_confidence_matches']}
- **Breakouts detected:** {summary['breakouts_detected']}

## 📊 Volume Trends
"""

        for trend, count in summary['volume_trend_distribution'].items():
            content += f"- **{trend}:** {count}\n"

        content += f"""

---
*Generated by VCP Screening Bot* 🤖
"""

        return content


if __name__ == "__main__":
    # Test the report generator
    from src.vcp_detector import VCPResult

    logging.basicConfig(level=logging.INFO)

    # Create sample VCP results for testing
    sample_results = {
        'AAPL': VCPResult(
            detected=True,
            confidence=0.85,
            contractions=[{'pullback_percentage': 15}, {'pullback_percentage': 10}],
            breakout_date=datetime.now(),
            breakout_price=175.50,
            base_length_days=45,
            volume_trend="decreasing",
            notes=["High confidence pattern", "Strong volume confirmation"]
        ),
        'MSFT': VCPResult(
            detected=False,
            confidence=0.35,
            contractions=[],
            breakout_date=None,
            breakout_price=None,
            base_length_days=0,
            volume_trend="insufficient_data",
            notes=["Insufficient contractions"]
        )
    }

    sample_data_summary = {
        'total_symbols': 2,
        'avg_data_points': 60,
        'date_range': {
            'earliest': datetime.now() - pd.Timedelta(days=60),
            'latest': datetime.now()
        }
    }

    generator = ReportGenerator()

    # Test CSV generation
    csv_path = generator.generate_csv_report(sample_results)
    print(f"Generated test CSV: {csv_path}")

    # Test summary generation
    summary = generator.generate_summary_report(sample_results, sample_data_summary, 45.2)
    generator.print_summary_to_console(summary)

    # Test JSON summary
    json_path = generator.save_summary_json(summary)
    print(f"Generated test JSON: {json_path}")