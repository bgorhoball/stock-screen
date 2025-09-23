# VCP Trading Strategy Testing Guide

## 🎯 Testing Overview

Your VCP trading strategy system now includes comprehensive testing at multiple levels:

1. **Local Development Testing** - Quick iteration and debugging
2. **GitHub Actions Testing** - Automated validation and deployment
3. **Integration Testing** - End-to-end pipeline validation

## 🏠 Local Testing Setup

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pandas, numpy, matplotlib, yfinance; print('✅ Dependencies installed')"
```

### Quick Tests

```bash
# 1. Run unit test suite
python test_suite.py

# 2. Run sample backtest (5 symbols)
python run_backtest.py --symbols "AAPL,MSFT,GOOGL,TSLA,NVDA" --max-symbols 5

# 3. Test paper trading
python paper_trader.py --mode single --capital 50000

# 4. Full pipeline test
python test_pipeline.py
```

## 🤖 GitHub Actions Testing

### Current Workflows

1. **Weekly Backtesting** (`.github/workflows/weekly-backtest.yml`)
   - **Schedule**: Sundays at 6 PM ET
   - **Purpose**: Validate strategy performance
   - **Manual**: Actions → "Weekly VCP Strategy Backtest" → Run workflow

2. **Paper Trading** (`.github/workflows/paper-trading.yml`)
   - **Schedule**: Daily at 7:30 PM ET (after VCP screening)
   - **Purpose**: Live trading simulation
   - **Manual**: Actions → "Paper Trading Simulation" → Run workflow

### Manual Testing Steps

1. **Go to GitHub Actions tab** in your repository
2. **Select workflow** to test
3. **Click "Run workflow"**
4. **Configure parameters** (if needed)
5. **Monitor execution** and check logs

## 📊 Testing with Real VCP Data

### Using Your VCP Candidates

Your production run found **61 VCP patterns** with high confidence. Test with these:

```bash
# Test backtest with your VCP candidates
python run_backtest.py --symbols vcp_candidates --start-date 2022-01-01

# Test paper trading with current VCP results
python paper_trader.py --mode single --vcp-file daily_reports/vcp_monitoring_candidates.json
```

### Example VCP Candidates from Your Results

- **CDNS**: 1.00 confidence, 3 contractions, 40-day base
- **WFC**: 0.95 confidence, 2 contractions, 34-day base
- **BIIB**: 0.90 confidence, 4 contractions, 65-day base

## 🔧 Testing Scenarios

### Scenario 1: Strategy Validation
```bash
# Test different confidence thresholds
python run_backtest.py --symbols top100 --min-confidence 0.9 --max-symbols 20

# Compare with lower threshold
python run_backtest.py --symbols top100 --min-confidence 0.7 --max-symbols 20
```

### Scenario 2: Risk Management Testing
```bash
# Test with aggressive settings
python run_backtest.py --symbols top100 --stop-loss 0.05 --profit-target 0.30

# Test with conservative settings
python run_backtest.py --symbols top100 --stop-loss 0.10 --profit-target 0.20
```

### Scenario 3: Paper Trading Simulation
```bash
# Start paper trading with your VCP candidates
python paper_trader.py --mode single --capital 100000

# Generate performance report
python paper_trader.py --mode single --report

# Monitor continuously (for development)
python paper_trader.py --mode monitor --interval 300
```

## 📈 Expected Results

### Backtest Performance (Based on VCP Research)
- **Win Rate**: 65-75%
- **Annual Return**: 25-40%
- **Max Drawdown**: 15-25%
- **Sharpe Ratio**: 1.5-2.5

### Your System Advantages
- **High-Quality Patterns**: 61 patterns with ≥0.7 confidence
- **Systematic Execution**: No emotional bias
- **Risk Management**: 2% portfolio risk per trade
- **Real-time Monitoring**: Precise breakout timing

## 🚨 Troubleshooting

### Common Issues

1. **Dependencies Missing**
   ```bash
   pip install -r requirements.txt
   ```

2. **Data Fetching Errors**
   - Check internet connection
   - Verify API keys (Alpha Vantage, Finnhub)
   - Try with fewer symbols first

3. **No VCP Candidates**
   - Run daily VCP screening first
   - Check `daily_reports/vcp_monitoring_candidates.json`

4. **GitHub Actions Failures**
   - Check repository secrets are set
   - Verify workflow permissions
   - Review action logs for detailed errors

### Debug Commands

```bash
# Test individual components
python -c "from src.vcp_detector import VCPDetector; print('VCP Detector OK')"
python -c "from src.data_fetcher import DataFetcher; print('Data Fetcher OK')"

# Test with verbose logging
python run_backtest.py --symbols "AAPL" --verbose

# Check portfolio state
python -c "
import json
with open('paper_portfolio.json', 'r') as f:
    data = json.load(f)
print(f'Cash: \${data[\"cash\"]:,.0f}')
print(f'Positions: {len(data[\"positions\"])}')
"
```

## 🎯 Testing Checklist

### Pre-Deployment Testing
- [ ] Unit tests pass (`python test_suite.py`)
- [ ] Sample backtest completes successfully
- [ ] Paper trading simulation works
- [ ] Reports generate correctly
- [ ] Telegram notifications work (if configured)

### GitHub Actions Testing
- [ ] Weekly backtest workflow runs manually
- [ ] Paper trading workflow runs manually
- [ ] Artifacts are generated and saved
- [ ] Telegram notifications are sent
- [ ] Repository commits work correctly

### Integration Testing
- [ ] VCP screening results feed into trading system
- [ ] Paper trading uses real VCP candidates
- [ ] Performance tracking works across sessions
- [ ] Risk management controls function properly

## 🚀 Next Steps

1. **Install Dependencies Locally**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Quick Test**
   ```bash
   python test_pipeline.py
   ```

3. **Test GitHub Actions**
   - Go to Actions tab → Run "Weekly VCP Strategy Backtest"
   - Monitor execution and download artifacts

4. **Monitor Live Performance**
   - Paper trading runs automatically after daily VCP screening
   - Weekly backtests validate strategy performance
   - Monthly optimization based on results

Your VCP trading strategy system is ready for comprehensive testing and deployment! 🎉