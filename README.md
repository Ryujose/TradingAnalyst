# Trading Analysis App

A professional-grade trading analysis application built with Python, Poetry, and clean architecture. It leverages LLMs (via LiteLLM) and yfinance to provide a comprehensive analysis of any stock.

## Features

1. **Company Health Analysis**: Detailed look at cash, debt, market valuation, and growth projections.
2. **Market Value Evaluation**: Assessment of whether the stock is undervalued, overvalued, or fairly valued based on its health.
3. **Technical Analysis**: Automatic identification of key support and resistance levels.
4. **Social Sentiment**: Analysis of recent news and social sentiment (Good/Bad).
5. **News Summary**: Bullish and bearish summary of the latest key data.
6. **Multi-Judge Perspective**: Evaluation from three professional viewpoints:
   - **Professional Trader**: Focused on price action and technicals.
   - **Professional Analyst**: Focused on fundamentals and valuation.
   - **Professional Risk Manager**: Focused on downside risks and stability.
7. **Final Recommendation**: A definitive "Buy", "Hold", or "Sell" response for the final user.

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

Run the analysis for any stock ticker:

```bash
poetry run python main.py AAPL
```

You can also specify a different model:

```bash
poetry run python main.py TSLA --model anthropic/claude-3-5-sonnet-20240620
```

## Architecture

The project follows Clean Architecture principles:
- `domain/`: Core business logic, models, and interfaces.
- `infrastructure/`: External implementations (Data providers, LLM services).
- `application/`: Use cases and orchestration.
- `main.py`: Entry point and CLI.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
