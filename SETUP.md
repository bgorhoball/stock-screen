# VCP Screening System Setup Guide

This guide will walk you through setting up the automated VCP screening system from scratch.

## 📋 Prerequisites

- GitHub account
- Basic familiarity with command line
- Python 3.11+ (for local testing)

## 🚀 Step-by-Step Setup

### 1. Repository Setup

#### Option A: Use this repository directly

1. **Fork this repository** to your GitHub account
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/stock-screen.git
   cd stock-screen
   ```

#### Option B: Create new repository

1. **Create a new repository** on GitHub
2. **Upload these files** to your repository
3. **Clone your repository** locally

### 2. Local Environment Setup (Optional)

For local testing and development:

```bash
# Create virtual environment
python -m venv vcp_env
source vcp_env/bin/activate  # On Windows: vcp_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 3. API Key Configuration (Optional but Recommended)

#### Alpha Vantage Setup (Free Tier)

1. **Sign up** at [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. **Get your free API key** (500 requests/day)
3. **Add to your repository secrets**:
   - Go to your GitHub repository
   - Click **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `ALPHA_VANTAGE_API_KEY`
   - Value: Your API key

> **Note**: Alpha Vantage is optional. The system works with yfinance alone, but Alpha Vantage provides backup data access.

### 4. Notification Setup (Optional)

#### Slack Notifications

1. **Create a Slack webhook**:
   - Go to your Slack workspace
   - Visit [Slack API Apps](https://api.slack.com/apps)
   - Click **Create New App** → **From scratch**
   - Choose app name and workspace
   - Go to **Incoming Webhooks** → **Activate**
   - Click **Add New Webhook to Workspace**
   - Choose channel and copy webhook URL

2. **Add webhook to repository secrets**:
   - Name: `SLACK_WEBHOOK_URL`
   - Value: Your webhook URL

#### Discord Notifications

1. **Create a Discord webhook**:
   - Go to your Discord server
   - Right-click on channel → **Edit Channel**
   - Go to **Integrations** → **Webhooks**
   - Click **New Webhook** → **Copy Webhook URL**

2. **Add webhook to repository secrets**:
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: Your webhook URL

### 5. GitHub Actions Configuration

#### Enable Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. If prompted, click **Enable GitHub Actions**

#### Test the Workflow

1. **Manual test run**:
   - Go to **Actions** tab
   - Click **Daily VCP Screening**
   - Click **Run workflow**
   - Set parameters:
     - `max_symbols`: 10 (for testing)
     - `dry_run`: true (for first test)
   - Click **Run workflow**

2. **Monitor the run**:
   - Click on the running workflow
   - Watch the real-time logs
   - Verify all steps complete successfully

### 6. Local Testing (Optional)

Test the system locally before automated deployment:

```bash
# Test ticker fetching
python -c "
import sys; sys.path.append('src')
from ticker_fetcher import SP500TickerFetcher
fetcher = SP500TickerFetcher()
tickers = fetcher.get_sp500_tickers()
print(f'Fetched {len(tickers)} tickers')
"

# Test with small sample
python vcp_screen.py --max-symbols 5 --verbose

# Test data fetching only
python vcp_screen.py --dry-run --max-symbols 3
```

### 7. Production Deployment

#### Schedule Configuration

The workflow is pre-configured to run:
- **Monday-Friday at 7 PM ET (11 PM UTC)**
- After market close and data updates

To modify the schedule, edit `.github/workflows/daily-vcp-screening.yml`:

```yaml
schedule:
  # Run at 7:00 PM ET (11:00 PM UTC) Monday-Friday
  - cron: '0 23 * * 1-5'
```

#### First Production Run

1. **Disable testing mode**:
   - Remove `max_symbols` parameter from workflow
   - Set `dry_run` to false

2. **Manual production test**:
   - Go to **Actions** → **Daily VCP Screening**
   - Click **Run workflow**
   - Leave default settings (will run full S&P 500)
   - Monitor execution (should take 10-30 minutes)

3. **Verify outputs**:
   - Check **Artifacts** for generated reports
   - Verify GitHub issue creation
   - Check notification channels

## 🔧 Configuration Customization

### VCP Detection Parameters

Edit `config/config.yaml` to customize screening criteria:

```yaml
vcp_parameters:
  min_contractions: 2           # Require at least 2 contractions
  max_contractions: 6           # Consider up to 6 contractions
  min_base_length_days: 7       # Minimum base formation period
  volume_decrease_threshold: 0.8 # Volume contraction requirement
  confidence_threshold: 0.5     # Minimum confidence for reporting
```

### Notification Preferences

```yaml
notifications:
  enabled: true
  channels:
    - "slack"           # Enable Slack notifications
    - "discord"         # Enable Discord notifications
    - "github_issues"   # Enable GitHub issue creation
```

### Data Source Configuration

```yaml
data_sources:
  primary: "yfinance"        # Primary data source
  fallback: "alpha_vantage"  # Fallback data source
  historical_weeks: 12       # Weeks of historical data
```

## 📊 Understanding the Output

### First Successful Run

After your first successful run, you'll see:

1. **GitHub Issue** created with daily report
2. **Artifacts** containing CSV and JSON files
3. **Notifications** sent to configured channels
4. **Repository commits** with reports (optional)

### Reading the Results

#### CSV Report Format

```csv
symbol,confidence,contractions_count,base_length_days,volume_trend,breakout_detected
AAPL,0.85,3,42,decreasing,true
MSFT,0.72,2,28,stable,false
```

#### Confidence Levels

- **0.8-1.0**: High confidence - strong VCP pattern
- **0.6-0.8**: Medium confidence - good pattern with minor issues
- **0.5-0.6**: Low confidence - weak pattern or limited data

### No Results Found

It's normal to have days with no VCP patterns detected:
- VCP patterns are relatively rare
- Market conditions affect pattern formation
- Strict criteria ensure quality matches

## 🚨 Troubleshooting Setup

### Common Setup Issues

#### 1. Workflow Fails with "Module not found"

**Solution**: Ensure `requirements.txt` is in repository root:
```bash
# Check if file exists
ls requirements.txt

# If missing, create it
cat > requirements.txt << EOF
yfinance>=0.2.28
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
python-dotenv>=1.0.0
alpha-vantage>=2.3.1
EOF
```

#### 2. No Data Retrieved

**Symptoms**: "No symbols with valid data" in logs

**Solutions**:
- Check internet connectivity in Actions environment
- Verify yfinance is not being rate-limited
- Ensure Alpha Vantage API key is valid (if configured)

#### 3. Notifications Not Working

**Symptoms**: Workflow succeeds but no notifications received

**Solutions**:
- Verify webhook URLs are correct in repository secrets
- Test webhooks manually with curl
- Check notification channel permissions

#### 4. Repository Secrets Not Found

**Symptoms**: "Secret not found" in workflow logs

**Solutions**:
- Go to repository **Settings** → **Secrets and variables** → **Actions**
- Verify secret names match workflow requirements
- Ensure secrets are set at repository level (not environment level)

### Testing Webhook URLs

#### Test Slack Webhook

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message from VCP setup"}' \
  YOUR_SLACK_WEBHOOK_URL
```

#### Test Discord Webhook

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"content":"Test message from VCP setup"}' \
  YOUR_DISCORD_WEBHOOK_URL
```

### Debugging Workflows

1. **Enable debug logging**:
   - Add `--verbose` flag to vcp_screen.py command in workflow

2. **Check Action logs**:
   - Go to **Actions** tab
   - Click on failed workflow run
   - Expand each step to see detailed logs

3. **Download artifacts**:
   - Failed runs may still produce partial results
   - Check artifacts for generated reports

## 🎯 Next Steps After Setup

### Week 1: Monitoring

- Check daily workflow execution
- Review generated reports
- Adjust notification preferences
- Monitor data quality

### Week 2: Optimization

- Analyze pattern detection accuracy
- Adjust VCP parameters if needed
- Review false positives/negatives
- Fine-tune confidence thresholds

### Month 1: Enhancement

- Add custom ticker lists for specific sectors
- Implement additional technical indicators
- Create custom notification templates
- Add backtesting capabilities

## 📞 Getting Help

If you encounter issues during setup:

1. **Check this guide** for common solutions
2. **Review workflow logs** in GitHub Actions
3. **Test components individually** using local Python scripts
4. **Open an issue** with detailed error information
5. **Include relevant logs** and configuration details

## ✅ Setup Checklist

- [ ] Repository created and cloned
- [ ] Dependencies installed (if testing locally)
- [ ] Alpha Vantage API key added to secrets (optional)
- [ ] Notification webhooks configured (optional)
- [ ] GitHub Actions enabled
- [ ] Test workflow executed successfully
- [ ] Configuration customized for preferences
- [ ] First production run completed
- [ ] Output verified (reports, notifications, artifacts)
- [ ] Monitoring schedule established

---

*Setup complete! Your VCP screening system is now ready for automated daily operation.* 🎉