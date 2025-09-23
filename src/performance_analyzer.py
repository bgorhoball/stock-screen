"""
Performance Analysis and Reporting for VCP Trading Strategy
Generates comprehensive reports, charts, and analysis of trading results
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
from dataclasses import asdict
from .backtester import BacktestResults
from .portfolio_manager import PortfolioManager, ClosedTrade, PortfolioStats

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Analyzes and reports on VCP trading strategy performance."""

    def __init__(self):
        """Initialize performance analyzer."""
        # Set style for plots
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    def generate_backtest_report(self, results: BacktestResults,
                                output_dir: str = "reports") -> str:
        """
        Generate comprehensive backtest report.

        Args:
            results: Backtest results
            output_dir: Directory to save reports

        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{output_dir}/backtest_report_{timestamp}.html"

        html_content = self._generate_html_report(results)

        # Ensure output directory exists
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save report
        with open(report_path, 'w') as f:
            f.write(html_content)

        logger.info(f"Backtest report generated: {report_path}")
        return report_path

    def generate_trade_analysis(self, trades: List[ClosedTrade],
                               output_dir: str = "reports") -> Dict:
        """
        Generate detailed trade analysis.

        Args:
            trades: List of closed trades
            output_dir: Directory to save analysis

        Returns:
            Dictionary with trade analysis metrics
        """
        if not trades:
            return {"error": "No trades to analyze"}

        # Convert to DataFrame for analysis
        trade_data = []
        for trade in trades:
            trade_data.append({
                'symbol': trade.symbol,
                'entry_date': trade.entry_date,
                'exit_date': trade.exit_date,
                'holding_days': trade.holding_days,
                'pnl_percent': trade.pnl_percent,
                'pnl_dollars': trade.pnl_dollars,
                'exit_reason': trade.exit_reason,
                'confidence': trade.confidence,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price
            })

        df = pd.DataFrame(trade_data)

        # Calculate analysis metrics
        analysis = {
            'total_trades': len(trades),
            'winning_trades': len(df[df['pnl_percent'] > 0]),
            'losing_trades': len(df[df['pnl_percent'] <= 0]),
            'win_rate': len(df[df['pnl_percent'] > 0]) / len(df),
            'avg_win': df[df['pnl_percent'] > 0]['pnl_percent'].mean(),
            'avg_loss': df[df['pnl_percent'] <= 0]['pnl_percent'].mean(),
            'best_trade': df['pnl_percent'].max(),
            'worst_trade': df['pnl_percent'].min(),
            'avg_holding_days': df['holding_days'].mean(),
            'profit_factor': self._calculate_profit_factor(trades),
            'by_exit_reason': df['exit_reason'].value_counts().to_dict(),
            'by_confidence': df.groupby(pd.cut(df['confidence'], bins=[0, 0.7, 0.8, 0.9, 1.0]))['pnl_percent'].mean().to_dict(),
            'monthly_performance': self._analyze_monthly_performance(df),
            'holding_period_analysis': self._analyze_holding_periods(df)
        }

        # Save detailed analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = f"{output_dir}/trade_analysis_{timestamp}.json"

        import os
        os.makedirs(output_dir, exist_ok=True)

        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)

        logger.info(f"Trade analysis saved: {analysis_path}")
        return analysis

    def create_performance_charts(self, results: BacktestResults,
                                 output_dir: str = "reports") -> List[str]:
        """
        Create performance visualization charts.

        Args:
            results: Backtest results
            output_dir: Directory to save charts

        Returns:
            List of paths to generated chart files
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        chart_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Portfolio Value Over Time
        chart_path = f"{output_dir}/portfolio_value_{timestamp}.png"
        self._create_portfolio_chart(results.portfolio_history, chart_path)
        chart_paths.append(chart_path)

        # 2. Drawdown Chart
        chart_path = f"{output_dir}/drawdown_{timestamp}.png"
        self._create_drawdown_chart(results.portfolio_history, chart_path)
        chart_paths.append(chart_path)

        # 3. Trade Analysis Charts
        if results.trade_history:
            chart_path = f"{output_dir}/trade_analysis_{timestamp}.png"
            self._create_trade_analysis_chart(results.trade_history, chart_path)
            chart_paths.append(chart_path)

            # 4. Monthly Returns Heatmap
            chart_path = f"{output_dir}/monthly_returns_{timestamp}.png"
            self._create_monthly_returns_heatmap(results.trade_history, chart_path)
            chart_paths.append(chart_path)

        logger.info(f"Generated {len(chart_paths)} performance charts")
        return chart_paths

    def compare_strategies(self, results_list: List[Tuple[str, BacktestResults]],
                          output_dir: str = "reports") -> str:
        """
        Compare multiple strategy configurations.

        Args:
            results_list: List of (strategy_name, results) tuples
            output_dir: Directory to save comparison

        Returns:
            Path to comparison report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_path = f"{output_dir}/strategy_comparison_{timestamp}.html"

        # Create comparison DataFrame
        comparison_data = []
        for name, results in results_list:
            comparison_data.append({
                'Strategy': name,
                'Total Return': f"{results.total_return:.1%}",
                'Annual Return': f"{results.annual_return:.1%}",
                'Sharpe Ratio': f"{results.sharpe_ratio:.2f}",
                'Max Drawdown': f"{results.max_drawdown:.1%}",
                'Win Rate': f"{results.win_rate:.1%}",
                'Profit Factor': f"{results.profit_factor:.2f}",
                'Avg Holding Days': f"{results.avg_holding_days:.1f}",
                'Number of Trades': results.num_trades
            })

        df = pd.DataFrame(comparison_data)

        # Generate HTML comparison
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VCP Strategy Comparison Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
                th {{ background-color: #f2f2f2; }}
                .best {{ background-color: #d4edda; }}
                .worst {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <h1>VCP Strategy Comparison Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>Performance Comparison</h2>
            {df.to_html(classes='table table-striped', escape=False, index=False)}

            <h2>Summary</h2>
            <p>Best performing strategy by total return: <strong>{self._get_best_strategy(results_list, 'total_return')}</strong></p>
            <p>Best risk-adjusted return (Sharpe): <strong>{self._get_best_strategy(results_list, 'sharpe_ratio')}</strong></p>
            <p>Lowest maximum drawdown: <strong>{self._get_best_strategy(results_list, 'max_drawdown', reverse=True)}</strong></p>
        </body>
        </html>
        """

        import os
        os.makedirs(output_dir, exist_ok=True)

        with open(comparison_path, 'w') as f:
            f.write(html_content)

        logger.info(f"Strategy comparison report generated: {comparison_path}")
        return comparison_path

    def generate_live_performance_summary(self, portfolio: PortfolioManager) -> Dict:
        """
        Generate live portfolio performance summary.

        Args:
            portfolio: Current portfolio manager

        Returns:
            Dictionary with performance summary
        """
        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_position_summary()
        recent_trades = portfolio.get_trade_history(limit=10)

        # Calculate additional metrics
        current_allocation = {}
        for pos in positions:
            current_allocation[pos['symbol']] = pos['shares'] * pos['current_price']

        total_invested = sum(current_allocation.values())
        cash_percentage = stats.cash / stats.total_value if stats.total_value > 0 else 0

        return {
            'portfolio_value': stats.total_value,
            'total_return': stats.total_return,
            'cash_percentage': cash_percentage,
            'num_positions': stats.num_positions,
            'unrealized_pnl': stats.unrealized_pnl,
            'realized_pnl': stats.realized_pnl,
            'win_rate': stats.win_rate,
            'avg_gain': stats.avg_gain,
            'avg_loss': stats.avg_loss,
            'max_drawdown': stats.max_drawdown,
            'sharpe_ratio': stats.sharpe_ratio,
            'current_positions': positions,
            'recent_trades': recent_trades,
            'top_performers': self._get_top_performers(positions),
            'worst_performers': self._get_worst_performers(positions),
            'last_updated': datetime.now().isoformat()
        }

    def _generate_html_report(self, results: BacktestResults) -> str:
        """Generate HTML backtest report."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VCP Strategy Backtest Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .metric {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>VCP Trading Strategy Backtest Report</h1>
            <p><strong>Period:</strong> {results.backtest_period}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>Performance Summary</h2>
            <div class="metric">
                <strong>Total Return:</strong> <span class="{'positive' if results.total_return > 0 else 'negative'}">{results.total_return:.1%}</span>
            </div>
            <div class="metric">
                <strong>Annualized Return:</strong> <span class="{'positive' if results.annual_return > 0 else 'negative'}">{results.annual_return:.1%}</span>
            </div>
            <div class="metric">
                <strong>Benchmark (SPY) Return:</strong> {results.benchmark_return:.1%}
            </div>
            <div class="metric">
                <strong>Alpha:</strong> <span class="{'positive' if results.alpha > 0 else 'negative'}">{results.alpha:.1%}</span>
            </div>

            <h2>Risk Metrics</h2>
            <div class="metric">
                <strong>Maximum Drawdown:</strong> <span class="negative">{results.max_drawdown:.1%}</span>
            </div>
            <div class="metric">
                <strong>Sharpe Ratio:</strong> {results.sharpe_ratio:.2f}
            </div>
            <div class="metric">
                <strong>Volatility:</strong> {results.volatility:.1%}
            </div>
            <div class="metric">
                <strong>Beta:</strong> {results.beta:.2f}
            </div>

            <h2>Trading Statistics</h2>
            <div class="metric">
                <strong>Total Trades:</strong> {results.num_trades}
            </div>
            <div class="metric">
                <strong>Win Rate:</strong> {results.win_rate:.1%}
            </div>
            <div class="metric">
                <strong>Average Gain:</strong> <span class="positive">{results.avg_gain:.1%}</span>
            </div>
            <div class="metric">
                <strong>Average Loss:</strong> <span class="negative">{results.avg_loss:.1%}</span>
            </div>
            <div class="metric">
                <strong>Profit Factor:</strong> {results.profit_factor:.2f}
            </div>
            <div class="metric">
                <strong>Average Holding Period:</strong> {results.avg_holding_days:.1f} days
            </div>

            <h2>Portfolio Details</h2>
            <div class="metric">
                <strong>Final Portfolio Value:</strong> ${results.final_value:,.0f}
            </div>
            <div class="metric">
                <strong>Total Trading Fees:</strong> ${results.total_fees:.0f}
            </div>
            <div class="metric">
                <strong>Symbols Tested:</strong> {results.symbols_tested}
            </div>
            <div class="metric">
                <strong>VCP Patterns Found:</strong> {results.vcp_patterns_found}
            </div>

            <h2>Trade History</h2>
            {self._trades_to_html_table(results.trade_history[-20:])}  <!-- Last 20 trades -->

        </body>
        </html>
        """

    def _trades_to_html_table(self, trades: List[ClosedTrade]) -> str:
        """Convert trades to HTML table."""
        if not trades:
            return "<p>No trades to display.</p>"

        table_html = """
        <table>
            <tr>
                <th>Symbol</th>
                <th>Entry Date</th>
                <th>Exit Date</th>
                <th>Days Held</th>
                <th>P&L %</th>
                <th>P&L $</th>
                <th>Exit Reason</th>
                <th>Confidence</th>
            </tr>
        """

        for trade in trades:
            pnl_class = "positive" if trade.pnl_percent > 0 else "negative"
            table_html += f"""
            <tr>
                <td>{trade.symbol}</td>
                <td>{trade.entry_date.strftime('%Y-%m-%d')}</td>
                <td>{trade.exit_date.strftime('%Y-%m-%d')}</td>
                <td>{trade.holding_days}</td>
                <td class="{pnl_class}">{trade.pnl_percent:.1%}</td>
                <td class="{pnl_class}">${trade.pnl_dollars:.0f}</td>
                <td>{trade.exit_reason}</td>
                <td>{trade.confidence:.2f}</td>
            </tr>
            """

        table_html += "</table>"
        return table_html

    def _create_portfolio_chart(self, portfolio_history: List[Dict], output_path: str) -> None:
        """Create portfolio value over time chart."""
        dates = [entry['date'] for entry in portfolio_history]
        values = [entry['portfolio_value'] for entry in portfolio_history]

        plt.figure(figsize=(12, 6))
        plt.plot(dates, values, linewidth=2)
        plt.title('Portfolio Value Over Time')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_drawdown_chart(self, portfolio_history: List[Dict], output_path: str) -> None:
        """Create drawdown chart."""
        values = [entry['portfolio_value'] for entry in portfolio_history]
        dates = [entry['date'] for entry in portfolio_history]

        # Calculate drawdown
        peak = values[0]
        drawdowns = []

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            drawdowns.append(-drawdown)  # Negative for plotting

        plt.figure(figsize=(12, 6))
        plt.fill_between(dates, drawdowns, 0, alpha=0.3, color='red')
        plt.plot(dates, drawdowns, color='red', linewidth=1)
        plt.title('Portfolio Drawdown')
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_trade_analysis_chart(self, trades: List[ClosedTrade], output_path: str) -> None:
        """Create trade analysis charts."""
        if not trades:
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # P&L Distribution
        pnl_values = [trade.pnl_percent * 100 for trade in trades]
        ax1.hist(pnl_values, bins=20, alpha=0.7, edgecolor='black')
        ax1.set_title('P&L Distribution (%)')
        ax1.set_xlabel('P&L (%)')
        ax1.set_ylabel('Frequency')
        ax1.axvline(0, color='red', linestyle='--', alpha=0.7)

        # Holding Period Distribution
        holding_days = [trade.holding_days for trade in trades]
        ax2.hist(holding_days, bins=15, alpha=0.7, edgecolor='black')
        ax2.set_title('Holding Period Distribution')
        ax2.set_xlabel('Days Held')
        ax2.set_ylabel('Frequency')

        # Exit Reasons
        exit_reasons = [trade.exit_reason for trade in trades]
        exit_counts = pd.Series(exit_reasons).value_counts()
        ax3.pie(exit_counts.values, labels=exit_counts.index, autopct='%1.1f%%')
        ax3.set_title('Exit Reasons')

        # Cumulative P&L
        cumulative_pnl = np.cumsum([trade.pnl_dollars for trade in trades])
        ax4.plot(range(len(cumulative_pnl)), cumulative_pnl)
        ax4.set_title('Cumulative P&L')
        ax4.set_xlabel('Trade Number')
        ax4.set_ylabel('Cumulative P&L ($)')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_monthly_returns_heatmap(self, trades: List[ClosedTrade], output_path: str) -> None:
        """Create monthly returns heatmap."""
        if not trades:
            return

        # Create monthly returns DataFrame
        monthly_returns = {}
        for trade in trades:
            month_key = trade.exit_date.strftime('%Y-%m')
            if month_key not in monthly_returns:
                monthly_returns[month_key] = []
            monthly_returns[month_key].append(trade.pnl_percent)

        # Aggregate monthly returns
        monthly_avg = {month: np.mean(returns) for month, returns in monthly_returns.items()}

        if len(monthly_avg) < 2:
            return  # Need at least 2 months

        # Create heatmap data
        dates = pd.to_datetime(list(monthly_avg.keys()))
        returns = list(monthly_avg.values())

        years = sorted(dates.year.unique())
        months = range(1, 13)

        heatmap_data = np.full((len(years), 12), np.nan)

        for date, ret in zip(dates, returns):
            year_idx = years.index(date.year)
            month_idx = date.month - 1
            heatmap_data[year_idx, month_idx] = ret * 100

        plt.figure(figsize=(12, max(6, len(years))))
        sns.heatmap(heatmap_data,
                   xticklabels=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                   yticklabels=years,
                   annot=True, fmt='.1f', cmap='RdYlGn', center=0)
        plt.title('Monthly Returns Heatmap (%)')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _calculate_profit_factor(self, trades: List[ClosedTrade]) -> float:
        """Calculate profit factor."""
        gross_profit = sum(t.pnl_dollars for t in trades if t.pnl_dollars > 0)
        gross_loss = abs(sum(t.pnl_dollars for t in trades if t.pnl_dollars <= 0))
        return gross_profit / gross_loss if gross_loss > 0 else np.inf

    def _analyze_monthly_performance(self, df: pd.DataFrame) -> Dict:
        """Analyze monthly performance patterns."""
        df['exit_month'] = pd.to_datetime(df['exit_date']).dt.month
        monthly_stats = df.groupby('exit_month')['pnl_percent'].agg(['mean', 'count']).to_dict()
        return monthly_stats

    def _analyze_holding_periods(self, df: pd.DataFrame) -> Dict:
        """Analyze performance by holding period."""
        df['holding_bins'] = pd.cut(df['holding_days'], bins=[0, 5, 15, 30, 60, np.inf],
                                   labels=['1-5', '6-15', '16-30', '31-60', '60+'])
        holding_stats = df.groupby('holding_bins')['pnl_percent'].agg(['mean', 'count']).to_dict()
        return holding_stats

    def _get_best_strategy(self, results_list: List[Tuple[str, BacktestResults]],
                          metric: str, reverse: bool = False) -> str:
        """Get best performing strategy by metric."""
        sorted_results = sorted(results_list,
                               key=lambda x: getattr(x[1], metric),
                               reverse=not reverse)
        return sorted_results[0][0]

    def _get_top_performers(self, positions: List[Dict]) -> List[Dict]:
        """Get top performing positions."""
        return sorted(positions, key=lambda x: x['unrealized_pnl'], reverse=True)[:5]

    def _get_worst_performers(self, positions: List[Dict]) -> List[Dict]:
        """Get worst performing positions."""
        return sorted(positions, key=lambda x: x['unrealized_pnl'])[:5]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test performance analyzer
    analyzer = PerformanceAnalyzer()

    # Create sample backtest results for testing
    from .backtester import BacktestResults

    sample_results = BacktestResults(
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
        portfolio_history=[],
        trade_history=[],
        backtest_period="2023-01-01 to 2024-01-01",
        symbols_tested=100,
        vcp_patterns_found=30
    )

    print("Testing performance analyzer...")
    report_path = analyzer.generate_backtest_report(sample_results)
    print(f"Sample report generated: {report_path}")