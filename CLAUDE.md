# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated daily S&P 500 VCP (Volatility Contraction Pattern) screening system that identifies stocks matching Mark Minervini's technical criteria. The system uses free market data APIs and open-source tools to generate daily reports of potential trading opportunities.

## Architecture

The system follows a modular architecture:

- **Data Layer**: Fetches S&P 500 ticker lists and historical price/volume data using free APIs (yfinance primary, Alpha Vantage fallback)
- **Pattern Detection**: Implements VCP screening logic to identify progressive price contractions with volume analysis
- **Reporting**: Generates daily CSV reports, JSON summaries, and GitHub issues with matched tickers and pattern statistics
- **Automation**: GitHub Actions workflow for scheduled execution with multi-channel notifications
- **Notifications**: Integrated Slack, Discord, GitHub Issues, and email reporting

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

6. **Main Screening Script** (`vcp_screen.py`)
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
```

## GitHub Actions Workflows

1. **Daily VCP Screening** (`.github/workflows/daily-vcp-screening.yml`)
   - Scheduled: Monday-Friday at 7 PM ET (11 PM UTC)
   - Manual trigger with parameters (max_symbols, dry_run)
   - Generates artifacts, creates GitHub issues, sends notifications
   - Commits daily reports to repository

2. **Testing Workflow** (`.github/workflows/test-vcp-screening.yml`)
   - Triggered on push/PR to main/develop branches
   - Tests all components with limited symbol set
   - Validates ticker fetching, data pipeline, and VCP detection

## Configuration System

**Main Config** (`config/config.yaml`):
- VCP detection parameters (contractions, volume thresholds, base length)
- Data source preferences and historical data requirements
- Screening filters (minimum price, volume, confidence thresholds)
- Notification channel preferences

**Environment Variables** (`.env`):
- `ALPHA_VANTAGE_API_KEY`: Optional API key for data fallback
- `SLACK_WEBHOOK_URL`: Slack notification webhook
- `DISCORD_WEBHOOK_URL`: Discord notification webhook

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
- Data requirement: 12 weeks of daily OHLCV for 500+ symbols

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
- Multiple channel support with independent failure handling
- Webhook validation and retry logic
- Fallback to GitHub issues if external notifications fail

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

## Integration Notes

**Existing Open-Source VCP Implementations**:
- Referenced `marco-hui-95/vcp_screener` for pattern detection logic
- Adapted `shiyu2011/cookstock` methodologies for Stage 2 filtering
- Custom implementation optimized for daily automation and reliability

**Market Data Ecosystem**:
- yfinance for broad compatibility and ease of use
- Alpha Vantage for enterprise-grade fallback data
- Wikipedia for dynamic S&P 500 constituent updates
- Multiple data validation layers for production reliability

This system represents a production-ready implementation of automated VCP screening suitable for daily operation with minimal maintenance requirements.