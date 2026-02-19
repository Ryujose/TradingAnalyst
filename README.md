# Trading Analysis App

A professional-grade trading analysis application built with Python, Poetry, and clean architecture. It leverages LLMs (via LiteLLM) and yfinance to provide a comprehensive analysis of any stock.

## Features

1. **Company Health Analysis**: Detailed look at cash, debt, market valuation, and growth projections.
2. **Market Value Evaluation**: Assessment of whether the stock is undervalued, overvalued, or fairly valued based on its health.
3. **Technical Analysis**: Automatic identification of key support and resistance levels.
4. **Social Sentiment**: Analysis of recent news and social sentiment (Good/Bad).
5. **News Summary**: Bullish and bearish summary of the latest key data.
6. **Multi-Judge Perspective**: Evaluation from three professional viewpoints:
   - **Professional Trader**: Focused on price action, technicals, and regime alignment.
   - **Professional Analyst**: Focused on fundamentals, valuation, and peer comparison.
   - **Professional Risk Manager**: Focused on downside risks (VaR), drawdown, and portfolio impact.
8. **Final Recommendation**: A definitive "Buy", "Hold", or "Sell" response for the final user.

## Support for any LLM

The app uses `litellm`, allowing you to use any major LLM provider:
- **Cloud Providers**: OpenAI (GPT-4), Anthropic (Claude), Google (Gemini), etc.
- **Local Providers**: 
  - **Ollama**: Use `--model ollama/llama3` (ensure Ollama is running).
  - **LM Studio**: Use `--model lm_studio/your-model-name` (ensure LM Studio's local server is running).

## Setup

1. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

2. Set up your environment variables:
   Copy `.env.example` to `.env` and add your API keys.
   ```bash
   cp .env.example .env
   ```

## Usage

### CLI Interface

The project now includes a powerful CLI interface built with `rich` and `typer`.

```bash
# Analyze a stock
poetry run python cli.py analyze -t AAPL -m ollama/mistral:7b

# Manage your portfolio
poetry run python cli.py portfolio

# See daily runners with momentum scoring
poetry run python cli.py runners --mode live

# Run a live streaming scanner
poetry run python cli.py runners --stream

# Backtest runners for a specific date
poetry run python cli.py runners --mode backtest --date 2024-02-15

# Manage catalysts and news
poetry run python cli.py news add --symbol TSLA --title "Earnings Beat" --source "Reuters" --type earnings --sentiment positive
poetry run python cli.py news list --symbol TSLA
poetry run python cli.py news fetch TSLA -m ollama/mistral:7b -catastr 1
```

### Catalyst-Aware Momentum Scanning
The `runners` command now integrates with the news module. If recent news (catalysts) exist for a ticker, the momentum score is adjusted based on:
- **Sentiment**: Positive catalysts increase the score; negative ones decrease it.
- **News Type**: Earnings, FDA approvals, and Guidance updates carry higher weight.
- **Strength**: Manually rated catalyst strength (1-5) scales the impact.

### Analysis with Custom Model

You can still run a single analysis via the CLI:

```bash
poetry run python cli.py analyze AAPL
```

### Configuration
- Portfolio is stored in `portfolio.json`.
- Analysis exports are saved to `analysis_export.json` and `analysis_export.csv`.

## Project Structure
- `trading_analysis/domain`: Core interfaces and data models.
- `trading_analysis/infrastructure`: Data providers (yfinance, ddgs) and quantitative engines.
- `trading_analysis/application`: High-level business logic and analyzer orchestration.
- `cli.py`: Main entry point for the interactive CLI.

## Token Usage & Costs Analysis

A single analysis run involves 7 LLM calls to process different aspects of the stock (Health, Value, Sentiment, 3 Judges, and Final Resolver).

### Estimated Token Consumption
For a standard stock analysis (e.g., AAPL):
- **Input Tokens**: ~10,000 - 15,000 tokens (includes financials, news titles, quantitative reports, and previous judge reasoning).
- **Output Tokens**: ~2,000 - 3,000 tokens (includes reasoning, summaries, and structured JSON decisions).

### Estimated Cost per Run
Based on standard model pricing (per 1M tokens):

| Model Class | Example Models | Est. Cost / Run |
| :--- | :--- | :--- |
| **Flagship** | GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro | **$0.06 - $0.12** |
| **Efficient** | GPT-4o-mini, Gemini 1.5 Flash | **<$0.005** |
| **Local** | Ollama (Llama 3), LM Studio | **Free ($0.00)** |

*Note: Gemini models often have a free tier via Google AI Studio for limited usage.*

### Cost Optimization Tips
1. **Use Efficient Models**: For daily tracking, `gpt-4o-mini` or `gemini-1.5-flash` provide excellent results at a fraction of the cost.
2. **Local Inference**: Use **Ollama** or **LM Studio** to run models locally on your hardware for zero token cost.
3. **Selective Analysis**: The modular architecture allows for future expansion where specific engines can be disabled to save tokens.

## Architecture

The project follows Clean Architecture principles:
- `domain/`: Core business logic, models, and interfaces.
- `infrastructure/`: External implementations (Data providers, LLM services).
- `application/`: Use cases and orchestration.
- `main.py`: Entry point and CLI.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
