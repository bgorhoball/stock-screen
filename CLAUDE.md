# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated daily S&P 500 VCP (Volatility Contraction Pattern) screening system that identifies stocks matching Mark Minervini's technical criteria. The system uses free market data APIs and open-source tools to generate daily reports, perform real-time breakout monitoring, execute paper trading simulations, and conduct weekly strategy backtests.

## Architecture

The system follows a modular architecture:

- **Data Layer**: Fetches S&P 500 ticker lists and historical price/volume data using free APIs (yfinance primary, Alpha Vantage fallback)
- **Pattern Detection**: Implements VCP screening logic to identify progressive price contractions with volume analysis
- **Real-time Monitoring**: Finnhub API integration for breakout detection during market hours
- **Paper Trading**: Simulated trading system with portfolio tracking and performance analysis
- **Backtesting**: Weekly strategy validation using historical data
- **Reporting**: Generates daily CSV reports, JSON summaries, and GitHub issues with matched tickers and pattern statistics
- **Automation**: Comprehensive GitHub Actions workflows for scheduled execution
- **Notifications**: Integrated Telegram bot for real-time alerts and daily summaries

## Key Components

1. **S&P 500 Universe Management** (`src/ticker_fetcher.py`)
   - Wikipedia scraping with yfinance fallback
   - Static ticker list as final fallback
   - Automatic ticker list updates and validation

2. **Data Fetching Module** (`src/data_fetcher.py`)
   - Primary: yfinance (free, unlimited for public repos)
   - Fallback: Alpha Vantage (500 requests/day free tier)
   - 12 weeks of OHLCV data per ticker with quality validation
   - Rate limiting and error handling for API reliability

3. **VCP Pattern Detection Engine** (`src/vcp_detector.py`)
   - Implements Mark Minervini's VCP methodology
   - Progressive contractions (2-6 pullbacks decreasing in magnitude)
   - Volume analysis (decreasing volume during contractions)
   - Breakout identification with volume confirmation
   - Confidence scoring (0.0-1.0) based on pattern quality

4. **Report Generation** (`src/report_generator.py`)
   - CSV exports with detailed pattern metrics
   - JSON summaries with execution statistics
   - GitHub issue content formatting
   - Console output with summary statistics

5. **Notification System** (`src/notifications.py`)
   - Slack webhook integration with rich formatting
   - Discord webhook with embed messages
   - Email content generation (HTML format)
   - Multi-channel notification coordination

6. **Telegram Bot Integration** (`src/telegram_bot.py`)
   - Private bot for VCP screening notifications
   - Real-time breakout alerts with volume confirmation
   - Daily screening summaries with top matches
   - Paper trading progress reports
   - Weekly backtest result notifications
   - System health and error alerts

7. **Paper Trading System** (`paper_trader.py`)
   - Simulated portfolio management with $100,000 initial capital
   - VCP-based entry signals from daily screening
   - Risk management with stop-loss and position sizing
   - Performance tracking and trade logging
   - Watchlist management for potential opportunities

8. **Strategy Backtesting** (`run_backtest.py`)
   - Historical VCP strategy validation
   - Configurable time periods and symbol sets
   - Performance metrics calculation (returns, Sharpe ratio, drawdown)
   - HTML report generation with detailed analysis

9. **External Script System** (`scripts/`)
   - `analyze_portfolio.py`: Paper trading portfolio analysis
   - `send_telegram.py`: Paper trading Telegram notifications
   - `send_backtest_telegram.py`: Weekly backtest result notifications
   - Resolves GitHub Actions YAML/Python integration issues

10. **Main Screening Script** (`vcp_screen.py`)
    - Command-line interface with multiple options
    - Configuration management via YAML
    - Progress tracking and error handling
    - Integration of all components

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full screening (all S&P 500 stocks)
python vcp_screen.py

# Test with limited symbols
python vcp_screen.py --max-symbols 10 --verbose

# Dry run (data fetching only)
python vcp_screen.py --dry-run --max-symbols 5

# Custom configuration
python vcp_screen.py --config custom_config.yaml

# Save to specific directory
python vcp_screen.py --output results/2024-01-15

# Load custom ticker list
python vcp_screen.py --input my_tickers.txt

# Test individual components
python src/ticker_fetcher.py
python src/data_fetcher.py
python src/vcp_detector.py
python src/report_generator.py
python src/notifications.py
python src/telegram_bot.py

# Paper trading commands
python paper_trader.py --mode single --verbose
python paper_trader.py --mode report
python scripts/analyze_portfolio.py

# Backtest commands
python run_backtest.py --symbols sp500 --start-date 2022-01-01 --end-date 2024-01-01
python run_backtest.py --symbols vcp_candidates --backtest-years 2 --verbose
```

## GitHub Actions Workflows

The system includes 7 automated workflows handling different aspects of VCP screening, monitoring, paper trading, and backtesting:

### 1. **Daily VCP Screening** (`.github/workflows/daily-vcp-screening.yml`)
   - **Schedule**: Monday-Friday at 7 PM ET (11 PM UTC) via cron: '0 23 * * 1-5'
   - **Manual Trigger**: Yes, with workflow_dispatch inputs (max_symbols, dry_run, force_production)
   - **Function**: Primary production workflow for daily S&P 500 screening
   - **Features**:
     - Production vs test mode detection based on trigger type
     - Artifact generation with 30-day retention
     - GitHub issue creation with formatted reports
     - VCP candidate list updates for real-time monitoring
     - Automatic repository commits for daily reports
   - **Technical Notes**: Uses pip caching, handles both scheduled and manual execution

### 2. **Real-time VCP Monitoring** (`.github/workflows/realtime-vcp-monitoring.yml`)
   - **Schedule**: Every 2 minutes during market hours via cron: '*/2 13-20 * * 1-5'
   - **Manual Trigger**: Yes, for testing monitoring functionality
   - **Function**: Real-time breakout detection for VCP candidates
   - **Features**:
     - Market hours validation (9:30 AM - 4:00 PM ET)
     - Finnhub API integration for real-time data
     - Volume-confirmed breakout detection
     - Instant Telegram alerts for trading opportunities
     - Automatic candidate management and cleanup
   - **Technical Notes**: Efficient API usage (60 calls/minute handles 20+ symbols)

### 3. **VCP System Status Check** (`.github/workflows/system-status.yml`)
   - **Schedule**: Monday-Friday at 6 PM ET (10 PM UTC) via cron: '0 22 * * 1-5'
   - **Manual Trigger**: Yes, for on-demand health checks
   - **Function**: Comprehensive system health monitoring
   - **Features**:
     - Telegram bot connectivity validation
     - Data source availability testing (yfinance, Alpha Vantage)
     - Ticker fetching reliability assessment
     - Workflow file presence verification
     - Health status Telegram notifications
   - **Technical Notes**: Pre-screening validation ensures reliable daily operations

### 4. **Production VCP Screening Test** (`.github/workflows/production-test.yml`)
   - **Schedule**: Manual trigger only with safety confirmation
   - **Manual Trigger**: Requires typing "CONFIRM" to prevent accidental execution
   - **Function**: Full production environment testing and benchmarking
   - **Features**:
     - Complete S&P 500 screening simulation (15-30 minutes)
     - Performance timing and analysis
     - Detection rate validation (expected 0.5-5%)
     - Artifact upload for detailed analysis
     - Production readiness verification
   - **Technical Notes**: Includes system dependencies installation for CI environment

### 5. **Test VCP Screening** (`.github/workflows/test-vcp-screening.yml`)
   - **Schedule**: Triggered on push/PR to main/develop branches
   - **Manual Trigger**: No (CI/CD only)
   - **Function**: Development testing and continuous integration
   - **Features**:
     - Component-level testing (ticker fetcher, data pipeline, VCP detector)
     - Limited symbol testing (10 stocks) for efficiency
     - Dependency validation and error handling testing
     - Build verification and code quality checks
   - **Technical Notes**: Includes system dependency installation (libxml2-dev, libxslt-dev)

### 6. **Paper Trading Simulation** (`.github/workflows/paper-trading.yml`)
   - **Schedule**: Monday-Friday at 7:30 PM ET (11:30 PM UTC) via cron: '30 23 * * 1-5'
   - **Manual Trigger**: Yes, with options for single/report mode and portfolio reset
   - **Function**: Automated paper trading using VCP candidates from daily screening
   - **Features**:
     - $100,000 simulated portfolio with realistic trade execution
     - VCP-based entry signals from daily screening results
     - Risk management with stop-loss and position sizing rules
     - Daily Telegram notifications with portfolio performance
     - Portfolio state persistence between runs
     - Trade logging and performance analytics
   - **Technical Notes**: Uses external scripts to avoid YAML/Python syntax conflicts

### 7. **Weekly VCP Strategy Backtest** (`.github/workflows/weekly-backtest.yml`)
   - **Schedule**: Every Sunday at 6:00 PM ET (10:00 PM UTC) via cron: '0 22 * * 0'
   - **Manual Trigger**: Yes, with configurable symbol sources, time periods, and confidence thresholds
   - **Function**: Historical validation of VCP strategy performance
   - **Features**:
     - Configurable backtest periods (1-5 years)
     - Multiple symbol sources (S&P 500, top 100, VCP candidates)
     - Performance metrics calculation (returns, Sharpe ratio, drawdown)
     - HTML report generation with detailed trade analysis
     - Weekly results archival and Telegram notifications
     - Automatic cleanup of old results (28-day retention)
   - **Technical Notes**: External script pattern for Telegram notifications

## Configuration System

**Main Config** (`config/config.yaml`):
- VCP detection parameters (contractions, volume thresholds, base length)
- Data source preferences and historical data requirements
- Screening filters (minimum price, volume, confidence thresholds)
- Notification channel preferences

**Environment Variables** (`.env`):
- `ALPHA_VANTAGE_API_KEY`: Optional API key for data fallback
- `FINNHUB_API_KEY`: Required for real-time monitoring (60 calls/minute free)
- `TELEGRAM_BOT_TOKEN`: Private Telegram bot token for notifications
- `TELEGRAM_CHAT_ID`: Target chat ID for Telegram messages
- `SLACK_WEBHOOK_URL`: Slack notification webhook (legacy)
- `DISCORD_WEBHOOK_URL`: Discord notification webhook (legacy)

## VCP Pattern Implementation

**Detection Criteria**:
- 2-6 progressive price contractions (each smaller than previous)
- Volume contraction during consolidation phases
- Price position near recent highs (within 25% of 52-week high)
- Minimum base length of 7 trading days
- Breakout confirmation with increased volume

**Confidence Scoring Algorithm**:
- Base score for having required contractions (0.3)
- Volume trend analysis (decreasing +0.25, stable +0.1)
- Position near highs (+0.15)
- Breakout detection (+0.15, +0.1 for volume confirmation)
- Pattern quality bonus for perfect progression (+0.1)

## Data Requirements and Constraints

**Free API Limits**:
- yfinance: Unlimited but subject to rate limiting/blocks
- Alpha Vantage: 500 requests/day, 5 requests/minute
- Finnhub: 60 calls/minute free tier for real-time data
- Data requirement: 12 weeks of daily OHLCV for 500+ symbols
- Real-time monitoring: 20+ symbols within rate limits

**GitHub Actions Constraints**:
- 6-hour job timeout (sufficient for full S&P 500 screening)
- 2,000 free minutes/month for private repos (unlimited for public)
- Scheduled jobs minimum 5-minute intervals
- Auto-disable after 60 days of repository inactivity

## Error Handling and Reliability

**Data Fetching**:
- Multi-API failover (yfinance → Alpha Vantage)
- Rate limiting with exponential backoff
- Data quality validation (missing values, price integrity)
- Graceful degradation for failed symbols

**Pattern Detection**:
- Input validation for all data requirements
- Exception handling with detailed error messages
- Confidence scoring to filter low-quality patterns
- Progress tracking for large symbol sets

**Notifications**:
- Primary: Telegram bot with comprehensive message formatting
- Multiple channel support with independent failure handling
- Webhook validation and retry logic
- Fallback to GitHub issues if external notifications fail
- Real-time breakout alerts with volume confirmation
- Daily summaries with top VCP matches and system status

## Testing and Validation

**Component Testing**:
- Each module includes standalone test execution
- Sample data validation with known patterns
- API connectivity and rate limit testing

**Integration Testing**:
- GitHub Actions workflow for automated testing
- Limited symbol set testing (10 symbols)
- End-to-end pipeline validation

**Manual Testing Commands**:
```bash
# Test ticker fetching reliability
python -c "from src.ticker_fetcher import SP500TickerFetcher; print(len(SP500TickerFetcher().get_sp500_tickers()))"

# Test data pipeline with error handling
python -c "from src.data_fetcher import DataFetcher; print(DataFetcher().fetch_multiple_stocks(['AAPL', 'INVALID'], weeks=4))"

# Test VCP detection with sample data
python -c "import yfinance as yf; from src.vcp_detector import VCPDetector; data = yf.Ticker('AAPL').history(period='6mo'); print(VCPDetector().detect_vcp(data, 'AAPL'))"
```

## Deployment and Monitoring

**Production Deployment**:
- GitHub Actions for completely free execution
- Public repository for unlimited compute minutes
- Artifact storage with 30-day retention
- Automatic issue creation for result tracking

**Monitoring Points**:
- Workflow execution success/failure rates
- Data fetching success rates by source
- VCP detection rates and confidence distributions
- Notification delivery success rates

**Maintenance Tasks**:
- Weekly review of detection accuracy
- Monthly analysis of false positive/negative rates
- Quarterly update of static ticker fallback list
- Semi-annual review of VCP parameter effectiveness

## External Script Architecture

**Problem Solved**: GitHub Actions YAML workflows cannot embed Python scripts using heredoc syntax due to conflicts between YAML indentation rules and bash script requirements (EOF markers must be at column 1).

**Solution**: External Python scripts in `scripts/` directory called by workflows:
- `scripts/analyze_portfolio.py`: Paper trading portfolio metrics and reporting
- `scripts/send_telegram.py`: Paper trading daily summary notifications
- `scripts/send_backtest_telegram.py`: Weekly backtest result notifications

**Benefits**:
- Eliminates f-string syntax errors with backslash characters
- Proper Python syntax highlighting and error detection
- Cleaner separation between workflow definition and script logic
- Easier testing and debugging of individual components
- Follows GitHub Actions best practices

**Implementation Pattern**:
```yaml
# Instead of:
- name: Send notification
  run: |
    python3 << 'EOF'
    # Complex Python script with potential syntax issues
    EOF

# Use:
- name: Send notification
  run: |
    python3 scripts/send_notification.py
```

## Paper Trading System

**Portfolio Management**:
- Initial capital: $100,000 simulated
- State persistence: JSON files for portfolio, watchlist, and alerts
- Position sizing: Risk-based allocation per trade
- Stop-loss management: Automatic exit on adverse moves

**Trading Logic**:
- Entry signals: High-confidence VCP breakouts from daily screening
- Exit signals: Stop-loss triggers, profit targets, pattern invalidation
- Watchlist management: Track potential opportunities
- Performance tracking: Trade-by-trade logging with metrics

**Reporting**:
- Daily portfolio summaries via Telegram
- Trade execution logs with entry/exit details
- Performance analytics (returns, win rate, drawdown)
- Position monitoring and unrealized P&L tracking

## Telegram Bot Integration

**TelegramBot Class** (`src/telegram_bot.py`):
- Private bot configuration with token and chat ID
- Message formatting with Markdown support
- Rate limiting and error handling
- Multiple notification types:
  - Daily VCP screening summaries
  - Real-time breakout alerts
  - Paper trading progress reports
  - Weekly backtest results
  - System health notifications

**Key Methods**:
- `send_message(text)`: Generic text message sending
- `send_daily_screening_report()`: Formatted daily VCP results
- `send_breakout_alert()`: Real-time trading opportunities
- `send_system_status()`: Health monitoring updates
- `validate_configuration()`: Bot connectivity testing

## Integration Notes

**Existing Open-Source VCP Implementations**:
- Referenced `marco-hui-95/vcp_screener` for pattern detection logic
- Adapted `shiyu2011/cookstock` methodologies for Stage 2 filtering
- Custom implementation optimized for daily automation and reliability

**Market Data Ecosystem**:
- yfinance for broad compatibility and ease of use
- Alpha Vantage for enterprise-grade fallback data
- Finnhub for real-time market data during trading hours
- Wikipedia for dynamic S&P 500 constituent updates
- Multiple data validation layers for production reliability

**Production Architecture**:
- 7 GitHub Actions workflows for comprehensive automation
- External script pattern for reliable workflow execution
- Telegram bot integration for real-time notifications
- Paper trading simulation with realistic portfolio management
- Weekly backtesting for strategy validation
- Comprehensive error handling and monitoring

This system represents a production-ready implementation of automated VCP screening with paper trading simulation and strategy backtesting, suitable for daily operation with minimal maintenance requirements.