# VCP Stock Screening System

An automated daily screening system for Volatility Contraction Pattern (VCP) opportunities across all S&P 500 stocks, based on Mark Minervini's technical analysis methodology.

## 🎯 Features

- **Automated Daily Screening**: Runs automatically via GitHub Actions at 7 PM ET (Monday-Friday)
- **VCP Pattern Detection**: Implements Mark Minervini's VCP methodology with 2-6 contractions
- **Two-Tier Monitoring**: Daily screening (all S&P 500) + real-time monitoring (VCP candidates)
- **Multi-API Architecture**: yfinance primary, Alpha Vantage backup, Finnhub real-time
- **Private Telegram Notifications**: Instant daily reports and real-time breakout alerts
- **Free Deployment**: Completely free using GitHub Actions and free-tier APIs
- **Comprehensive Reporting**: CSV exports, JSON summaries, and detailed analysis

## 📊 What is VCP?

Volatility Contraction Pattern (VCP) is a stock setup developed by Mark Minervini that identifies potential breakout opportunities through:

- **Progressive Contractions**: 2-6 price pullbacks that decrease in magnitude
- **Volume Confirmation**: Volume decreases during contractions
- **Base Formation**: Price consolidation near 52-week highs
- **Breakout Setup**: Price break above resistance with increased volume

## 🚀 Quick Start

### 1. Repository Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd stock-screen

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy and configure the environment file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required: Telegram bot for notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional: API keys for enhanced functionality
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
```

**📱 Telegram Setup Required**: Follow [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for step-by-step bot creation.

### 3. Manual Testing

Run a test screening with limited symbols:

```bash
# Test with 10 symbols
python vcp_screen.py --max-symbols 10 --verbose

# Dry run (fetch data only)
python vcp_screen.py --dry-run --max-symbols 5
```

### 4. GitHub Actions Setup

1. **Repository Secrets**: Add these secrets in your GitHub repository settings:
   - `TELEGRAM_BOT_TOKEN` (required, for notifications)
   - `TELEGRAM_CHAT_ID` (required, for notifications)
   - `ALPHA_VANTAGE_API_KEY` (optional, for data fallback)
   - `FINNHUB_API_KEY` (optional, for real-time monitoring)

2. **Enable Actions**: Ensure GitHub Actions are enabled in your repository

3. **Manual Trigger**: Test the workflow manually from the Actions tab

## 📋 Usage

### Command Line Options

```bash
python vcp_screen.py [OPTIONS]

Options:
  -i, --input FILE          Input file with ticker symbols (one per line)
  -o, --output DIR          Output directory for reports (default: daily_reports)
  -c, --config FILE         Configuration file (default: config/config.yaml)
  -m, --max-symbols N       Maximum symbols to process (for testing)
  -v, --verbose             Enable verbose logging
  --dry-run                 Fetch data only, skip analysis
```

### Examples

```bash
# Full S&P 500 screening
python vcp_screen.py

# Custom ticker list
python vcp_screen.py --input my_tickers.txt

# Test with verbose output
python vcp_screen.py --max-symbols 20 --verbose

# Save to custom directory
python vcp_screen.py --output results/2024-01-15
```

## 📁 Project Structure

```
stock-screen/
├── src/                          # Core modules
│   ├── ticker_fetcher.py        # S&P 500 ticker fetching
│   ├── data_fetcher.py          # Historical data with failover
│   ├── vcp_detector.py          # VCP pattern detection
│   ├── report_generator.py      # Report generation
│   └── notifications.py         # Multi-channel notifications
├── .github/workflows/           # GitHub Actions
│   ├── daily-vcp-screening.yml # Daily automated screening
│   └── test-vcp-screening.yml  # Testing workflow
├── config/
│   └── config.yaml              # Configuration settings
├── daily_reports/               # Generated reports
├── vcp_screen.py               # Main screening script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## ⚙️ Configuration

### VCP Parameters (`config/config.yaml`)

```yaml
vcp_parameters:
  min_contractions: 2           # Minimum contractions required
  max_contractions: 6           # Maximum contractions to consider
  min_base_length_days: 7       # Minimum base formation length
  volume_decrease_threshold: 0.8 # Volume contraction threshold
  max_pullback_percentage: 50.0  # Maximum pullback size
  min_price: 10.0               # Minimum stock price
  min_average_volume: 100000    # Minimum average volume
```

### Data Sources

- **Primary**: yfinance (free, unlimited for public repos)
- **Fallback**: Alpha Vantage (500 requests/day free tier)
- **Historical Data**: 12 weeks of daily OHLCV data

## 📊 Output Reports

### CSV Report (`daily_reports/vcp_matches_YYYYMMDD.csv`)

| Column | Description |
|--------|-------------|
| symbol | Stock ticker symbol |
| confidence | Detection confidence (0.0-1.0) |
| contractions_count | Number of contractions found |
| base_length_days | Length of base in trading days |
| volume_trend | Volume behavior (decreasing/stable/increasing) |
| breakout_detected | Whether breakout was detected |
| breakout_date | Date of breakout (if detected) |
| breakout_price | Price of breakout (if detected) |
| pullback_range_min | Smallest pullback percentage |
| pullback_range_max | Largest pullback percentage |
| notes | Detailed analysis notes |

### Summary JSON (`daily_reports/vcp_summary_YYYYMMDD.json`)

Contains execution statistics, data quality metrics, and pattern distribution analysis.

## 🔔 Notifications

### Slack Integration

1. Create a Slack webhook in your workspace
2. Add `SLACK_WEBHOOK_URL` to repository secrets
3. Automatic notifications include:
   - Daily summary statistics
   - Top 5 high-confidence matches
   - Breakout alerts

### Discord Integration

1. Create a Discord webhook in your server
2. Add `DISCORD_WEBHOOK_URL` to repository secrets
3. Rich embed notifications with pattern details

### GitHub Issues

Automatic daily issues created with:
- Markdown-formatted reports
- Complete match listings
- Searchable by date and labels

## 🧪 Testing

### Unit Tests

```bash
# Run individual module tests
python src/ticker_fetcher.py
python src/data_fetcher.py
python src/vcp_detector.py
python src/report_generator.py
```

### GitHub Actions Testing

The repository includes automated testing that:
- Validates ticker fetching
- Tests data pipeline with sample symbols
- Verifies VCP detection logic
- Ensures report generation works

## 🔧 Troubleshooting

### Common Issues

1. **yfinance Rate Limiting**
   - Solution: Configured Alpha Vantage fallback
   - Rate limits are automatically handled

2. **GitHub Actions Timeout**
   - 6-hour limit is sufficient for full S&P 500 screening
   - Retry logic included for transient failures

3. **Missing Data**
   - Data quality validation built-in
   - Graceful handling of failed ticker fetches

4. **No VCP Patterns Found**
   - Normal market behavior
   - Adjust confidence thresholds in config if needed

### Debug Mode

```bash
# Enable verbose logging
python vcp_screen.py --verbose

# Test with minimal symbols
python vcp_screen.py --max-symbols 5 --verbose
```

## 📈 VCP Pattern Criteria

The system implements Mark Minervini's VCP methodology:

### Pattern Requirements

1. **Contractions**: 2-6 progressive price pullbacks
2. **Volume**: Decreasing volume during contractions
3. **Position**: Price near 52-week highs (within 25%)
4. **Quality**: Each pullback smaller than the previous
5. **Base**: Minimum 7-day consolidation period

### Confidence Scoring

- **0.8-1.0**: High confidence (strong pattern, volume confirmation)
- **0.5-0.8**: Medium confidence (good pattern, some confirmation)
- **0.0-0.5**: Low confidence (weak pattern or insufficient data)

## 🚦 Deployment Options

### GitHub Actions (Recommended)

- **Cost**: Free for public repositories
- **Schedule**: Daily at 7 PM ET (Monday-Friday)
- **Storage**: 30-day report retention
- **Notifications**: Multi-channel support

### Local Execution

```bash
# Set up cron job for daily execution
0 19 * * 1-5 /usr/bin/python3 /path/to/vcp_screen.py
```

### Cloud Deployment

Can be deployed to any cloud platform supporting Python:
- AWS Lambda (with scheduled CloudWatch events)
- Google Cloud Functions
- Azure Functions
- Heroku Scheduler

## 📜 License

This project is provided for educational and research purposes. Please ensure compliance with data provider terms of service.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📚 References

- [Mark Minervini's VCP Methodology](https://www.minervini.com/)
- [Think and Trade Like a Champion](https://www.amazon.com/Think-Trade-Like-Champion-Strategies/dp/0071774319)
- [yfinance Documentation](https://github.com/ranaroussi/yfinance)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review GitHub Actions logs
3. Open an issue with detailed error information
4. Include relevant log output and configuration

---

*Generated by Claude Code - Your AI-powered development assistant* 🤖