import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.columns import Columns
import os
from typing import Optional
from datetime import datetime

from trading_analysis.infrastructure.portfolio_manager import PortfolioManager
from trading_analysis.infrastructure.runners_data import YFinanceRunnersProvider
from trading_analysis.infrastructure.engines.runners_scoring import MomentumScoringEngine
from trading_analysis.application.runners_service import DefaultRunnersService
from trading_analysis.infrastructure.persistence import SQLAlchemyRunnersPersistence, SQLAlchemyNewsRepository
from trading_analysis.application.news_service import DefaultNewsService
from trading_analysis.infrastructure.engines.backtest_engine import MomentumBacktestEngine
from trading_analysis.application.analyzer import StockAnalyzer
from trading_analysis.infrastructure.aggregated_data import AggregatedDataProvider
from trading_analysis.infrastructure.llm_service import LiteLLMService
from trading_analysis.infrastructure.engines.risk_engine import YFinanceRiskEngine
from trading_analysis.infrastructure.engines.market_regime import YFinanceMarketRegimeEngine
from trading_analysis.infrastructure.engines.portfolio_engine import YFinancePortfolioImpactEngine
from trading_analysis.infrastructure.engines.relative_strength import YFinanceRelativeStrengthEngine
from trading_analysis.infrastructure.engines.monte_carlo import GBM_MonteCarloEngine
from trading_analysis.application.exporter import DataExporter

app = typer.Typer(help="Trading Analyst CLI")
news_app = typer.Typer(help="Manage stock news and catalysts")
app.add_typer(news_app, name="news")

console = Console()
portfolio_manager = PortfolioManager()

def get_news_service(model: Optional[str] = None):
    repo = SQLAlchemyNewsRepository()
    llm = LiteLLMService(model) if model else None
    return DefaultNewsService(repo, llm)

@news_app.command("add")
def news_add(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Stock ticker"),
    title: str = typer.Option(..., "--title", "-t", help="News title"),
    source: str = typer.Option(..., "--source", help="Publisher/Source"),
    news_type: str = typer.Option("other", "--type", help="earnings, guidance, FDA, merger, acquisition, offering, dilution, contract, analyst_upgrade, analyst_downgrade, macro, other"),
    sentiment: str = typer.Option("neutral", "--sentiment", help="positive, neutral, negative"),
    strength: int = typer.Option(1, "--strength", help="Catalyst strength (1-5)"),
    content: Optional[str] = typer.Option(None, "--content", help="Full text content"),
    link: Optional[str] = typer.Option(None, "--link", help="URL to news")
):
    """Add a new catalyst/news entry."""
    service = get_news_service()
    news = service.add_news(
        symbol=symbol, title=title, publisher=source, 
        news_type=news_type, sentiment=sentiment, 
        catalyst_strength=strength, content=content, link=link
    )
    rprint(f"[green]Added news with ID: {news.id} for {news.symbol}[/green]")

@news_app.command("update")
def news_update(
    news_id: int = typer.Option(..., "--id", help="News entry ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    sentiment: Optional[str] = typer.Option(None, "--sentiment"),
    strength: Optional[int] = typer.Option(None, "--strength"),
    content: Optional[str] = typer.Option(None, "--content")
):
    """Update an existing news entry."""
    service = get_news_service()
    try:
        news = service.update_news(
            news_id=news_id, title=title, content=content, 
            sentiment=sentiment, catalyst_strength=strength
        )
        rprint(f"[green]Updated news ID {news.id}[/green]")
    except ValueError as e:
        rprint(f"[red]{e}[/red]")

@news_app.command("delete")
def news_delete(
    news_id: int = typer.Option(..., "--id", help="News entry ID"),
    force: bool = typer.Option(False, "--force", help="Physically delete instead of soft-delete")
):
    """Delete a news entry."""
    service = get_news_service()
    service.delete_news(news_id, force=force)
    rprint(f"[yellow]Deleted news ID {news_id}[/yellow]")

@news_app.command("list")
def news_list(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Filter by ticker")
):
    """List recent news entries."""
    service = get_news_service()
    news_items = service.list_news(symbol=symbol)
    
    if not news_items:
        rprint("[yellow]No news entries found.[/yellow]")
        return
        
    table = Table(title=f"Recent News{' for ' + symbol.upper() if symbol else ''}", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Type")
    table.add_column("Sentiment")
    table.add_column("Str", justify="right")
    table.add_column("Title")
    table.add_column("Source")
    
    for n in news_items:
        sent_color = "green" if n.sentiment == "positive" else "red" if n.sentiment == "negative" else "white"
        table.add_row(
            str(n.id), n.symbol, n.news_type, f"[{sent_color}]{n.sentiment}[/{sent_color}]", 
            str(n.catalyst_strength), n.title, n.publisher
        )
    console.print(table)

@news_app.command("search")
def news_search(
    keyword: str = typer.Argument(..., help="Keyword to search in title or content")
):
    """Search news entries by keyword."""
    service = get_news_service()
    news_items = service.search_news(keyword)
    
    if not news_items:
        rprint(f"[yellow]No news entries found for '{keyword}'.[/yellow]")
        return
        
    table = Table(title=f"Search Results: {keyword}", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Title")
    
    for n in news_items:
        table.add_row(str(n.id), n.symbol, n.title)
    console.print(table)

@news_app.command("link")
def news_link(
    news_id: int = typer.Option(..., "--news-id", help="News ID"),
    runner_id: str = typer.Option(..., "--runner-id", help="Runner ID (e.g. 20250218-TSLA)")
):
    """Link a news entry to a detected runner."""
    service = get_news_service()
    link = service.link_news_to_runner(runner_id, news_id)
    rprint(f"[green]Linked news {news_id} to runner {runner_id}[/green]")

@news_app.command("fetch")
def news_fetch(
    symbol: str = typer.Argument(..., help="Stock ticker to fetch news for"),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="LLM model for categorization"),
    catalyst_strength: float = typer.Option(1, "--catalyst_strength", "-catastr", help="Catalyst strength threshold for news categorization")
):
    """Fetch and automatically categorize news from Google News RSS."""
    service = get_news_service(model)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Fetching and categorizing news for {symbol.upper()}...", total=None)
        new_items = service.auto_ingest_news(symbol, catalyst_strength)
    
    if not new_items:
        rprint(f"[yellow]No new news found for {symbol.upper()}.[/yellow]")
    else:
        rprint(f"[green]Successfully ingested {len(new_items)} new news items for {symbol.upper()}.[/green]")
        table = Table(title=f"New Catalysts for {symbol.upper()}", show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Sentiment")
        table.add_column("Str", justify="right")
        table.add_column("Title")
        
        for n in new_items:
            sent_color = "green" if n.sentiment == "positive" else "red" if n.sentiment == "negative" else "white"
            table.add_row(n.news_type, f"[{sent_color}]{n.sentiment}[/{sent_color}]", str(n.catalyst_strength), n.title)
        console.print(table)

@news_app.command("unlink")
def news_unlink(
    news_id: int = typer.Option(..., "--news-id", help="News ID"),
    runner_id: str = typer.Option(..., "--runner-id", help="Runner ID")
):
    """Unlink a news entry from a runner."""
    service = get_news_service()
    service.unlink_news_from_runner(runner_id, news_id)
    rprint(f"[yellow]Unlinked news {news_id} from runner {runner_id}[/yellow]")

def get_analyzer(model: str):
    data_provider = AggregatedDataProvider()
    llm_service = LiteLLMService(model)
    news_service = get_news_service(model) # Added news service
    risk_engine = YFinanceRiskEngine()
    regime_engine = YFinanceMarketRegimeEngine()
    portfolio_engine = YFinancePortfolioImpactEngine()
    rs_engine = YFinanceRelativeStrengthEngine()
    mc_engine = GBM_MonteCarloEngine()
    
    return StockAnalyzer(
        data_provider=data_provider,
        llm_service=llm_service,
        news_service=news_service,
        risk_engine=risk_engine,
        regime_engine=regime_engine,
        portfolio_engine=portfolio_engine,
        rs_engine=rs_engine,
        mc_engine=mc_engine
    )

@app.command()
def analyze(
        ticker: str = typer.Option("AAPL", "--ticker", "-t", help="Stock ticker to analyze"),
        model: str = typer.Option("ollama/llama3", "--model", "-m",  help="LLM model to use (e.g., gpt-4o, ollama/llama3, lm_studio/model)"),
        catalyst_strength: float = typer.Option(1, "--catalyst_strength", "-catastr", help="Catalyst strength threshold for news categorization")):
    """Analyze a specific stock ticker."""
    analyzer = get_analyzer(model)
    full_portfolio = portfolio_manager.get_portfolio()
    # Extract only weights for the quantitative engine
    weights_only = {t: item.weight for t, item in full_portfolio.items()}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Analyzing {ticker}...", total=None)
        analysis = analyzer.run_analysis(ticker, weights_only, catalyst_strength)
    
    # Display results
    rprint(Panel(f"[bold blue]Analysis Results for {ticker}[/bold blue]", expand=True))
    
    # Quantitative Insights Table
    q_table = Table(title="[bold]Quantitative Insights[/bold]", show_header=True, header_style="bold magenta", expand=True)
    q_table.add_column("Metric", style="dim")
    q_table.add_column("Value")
    
    if analysis.market_regime:
        q_table.add_row("Market Regime", f"{analysis.market_regime.regime_type} (Conf: {analysis.market_regime.regime_confidence:.2f})")
    
    if analysis.risk_metrics:
        q_table.add_row("1Y Volatility", f"{analysis.risk_metrics.volatility_1y:.2%}")
        q_table.add_row("Beta vs SPY", f"{analysis.risk_metrics.beta:.2f}")
        q_table.add_row("Sharpe Ratio", f"{analysis.risk_metrics.sharpe_ratio:.2f}")

    if analysis.monte_carlo:
        q_table.add_row("MC Median Return (1Y)", f"{analysis.monte_carlo.median_return:+.2%}")
        q_table.add_row("Prob of +20% move", f"{analysis.monte_carlo.prob_up_20:.2%}")

    console.print(q_table)

    # Judge Opinions
    rprint("\n[bold]Expert Judge Opinions[/bold]")
    opinions = []
    for opinion in [analysis.trader_opinion, analysis.analyst_opinion, analysis.risk_pro_opinion]:
        color = "green" if opinion.recommendation == "Buy" else "red" if opinion.recommendation == "Sell" else "yellow"
        opinions.append(Panel(
            f"[bold {color}]{opinion.recommendation}[/bold {color}]\n\n{opinion.opinion}",
            title=f"[bold]{opinion.role}[/bold]",
            border_style=color,
            width=40
        ))
    console.print(Columns(opinions))

    # Final Decision Panel
    fd = analysis.final_decision
    fd_color = "green" if fd.recommendation == "Buy" else "red" if fd.recommendation == "Sell" else "yellow"
    
    fd_text = f"[bold {fd_color}]Recommendation: {fd.recommendation}[/bold {fd_color}]\n"
    fd_text += f"Conviction Score: [bold]{fd.conviction_score}/100[/bold]\n"
    fd_text += f"Risk-Adjusted Rating: [bold]{fd.risk_adjusted_rating}/5.0[/bold]\n"
    fd_text += f"Suggested Position Size: [bold]{fd.position_size_suggestion*100:.2f}%[/bold]\n"
    fd_text += f"Agreement Index: [bold]{fd.agreement_index:.2f}[/bold]"

    rprint(Panel(fd_text, title="[bold]FINAL DECISION[/bold]", border_style=fd_color, expand=True))

    # Drivers and Risks in a table
    dr_table = Table.grid(expand=True)
    dr_table.add_column("Drivers", style="green")
    dr_table.add_column("Risks", style="red")
    
    drivers_list = "\n".join([f"• {d}" for d in fd.primary_drivers])
    risks_list = "\n".join([f"• {r}" for r in fd.key_risks])
    
    dr_table.add_row(
        Panel(drivers_list, title="[bold green]Primary Drivers[/bold green]"),
        Panel(risks_list, title="[bold red]Key Risks[/bold red]")
    )
    console.print(dr_table)
    
    # Export option
    export = typer.confirm("Do you want to export this analysis?")
    if export:
        DataExporter.to_json(analysis)
        DataExporter.to_csv(analysis)
        rprint("[green]Exported to analysis_export.json and analysis_export.csv[/green]")

@app.command()
def portfolio():
    """Manage your portfolio and track performance."""
    import yfinance as yf
    while True:
        p = portfolio_manager.get_portfolio()
        if not p:
            rprint("[yellow]Portfolio is empty.[/yellow]")
        else:
            # Fetch current prices for performance tracking
            tickers = list(p.keys())
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching current market data...", total=None)
                try:
                    data = yf.download(tickers, period="1d", progress=False)['Close']
                    if len(tickers) == 1:
                        current_prices = {tickers[0]: float(data.iloc[-1])}
                    else:
                        current_prices = {t: float(data[t].iloc[-1]) for t in tickers if t in data.columns}
                except Exception:
                    current_prices = {}

            table = Table(title="Current Portfolio", show_header=True, header_style="bold green")
            table.add_column("Ticker", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Weight", justify="right")
            table.add_column("Entry Price", justify="right")
            table.add_column("Current Price", justify="right")
            table.add_column("P&L %", justify="right")
            
            for ticker, item in p.items():
                curr = current_prices.get(ticker)
                entry = item.entry_price
                
                price_str = f"${entry:.2f}" if entry else "N/A"
                curr_str = f"${curr:.2f}" if curr else "N/A"
                
                pnl_str = "N/A"
                if curr and entry:
                    pnl = (curr - entry) / entry * 100
                    color = "green" if pnl >= 0 else "red"
                    pnl_str = f"[{color}]{pnl:+.2f}%[/{color}]"
                
                table.add_row(
                    ticker, 
                    item.name or "N/A", 
                    f"{item.weight*100:.1f}%", 
                    price_str,
                    curr_str,
                    pnl_str
                )
            
            console.print(table)
            rprint("\n[dim]Use these insights for Scalping (short), Swing (medium), or Long Term decisions.[/dim]")
        
        choice = typer.prompt("\n(a)dd/update, (r)emove, (q)uit portfolio mgmt", default="q")
        if choice == 'a':
            t = typer.prompt("Ticker").upper()
            w_str = typer.prompt("Weight (e.g. 0.1 for 10%)")
            try:
                w = float(w_str)
                p_val_str = typer.prompt("Entry Price (optional, press enter to skip)", default="")
                p_val = float(p_val_str) if p_val_str else None
                
                portfolio_manager.update_ticker(t, w, entry_price=p_val)
                rprint(f"[green]Updated {t}[/green]")
            except ValueError:
                rprint("[red]Invalid input. Please enter numbers for weight and price.[/red]")
        elif choice == 'r':
            t = typer.prompt("Ticker to remove").upper()
            portfolio_manager.remove_ticker(t)
            rprint(f"[yellow]Removed {t}[/yellow]")
        elif choice == 'q':
            break

@app.command()
def runners(
    mode: str = typer.Option("live", "--mode", "-m", help="Mode: live, premarket, backtest"),
    top_n: int = typer.Option(10, "--top", "-t", help="Number of top runners to show"),
    json_out: bool = typer.Option(False, "--json", help="Output in JSON format"),
    csv_out: bool = typer.Option(False, "--csv", help="Output in CSV format"),
    date: str = typer.Option(None, "--date", help="Date for backtest (YYYY-MM-DD)"),
    live_loop: bool = typer.Option(False, "--stream", "-s", help="Run in a continuous live loop")
):
    """Catch the daily runners with momentum scoring."""
    provider = YFinanceRunnersProvider()
    news_repo = SQLAlchemyNewsRepository()
    scoring_engine = MomentumScoringEngine(news_repository=news_repo)
    persistence = SQLAlchemyRunnersPersistence() 
    
    service = DefaultRunnersService(provider, scoring_engine, persistence)
    
    if mode == "backtest":
        if not date:
            rprint("[red]Date is required for backtest mode.[/red]")
            return
        
        bt_engine = MomentumBacktestEngine(news_repository=news_repo)
        bt_date = datetime.strptime(date, '%Y-%m-%d')
        
        # For backtest, we might need a list of tickers that were runners on that day.
        # Since we don't have that easily, we check if we have history in DB for that day
        # or ask for tickers.
        history = persistence.get_history(start_date=bt_date)
        tickers = list(set([h.ticker for h in history]))
        
        if not tickers:
            # Fallback: let the user provide tickers or use a sample for demo
            rprint("[yellow]No historical data found in DB for this date. Provide tickers to backtest or scan live first.[/yellow]")
            ticker_input = typer.prompt("Enter tickers to backtest (comma separated)", default="NVDA,TSLA,AMD,AAPL")
            tickers = [t.strip().upper() for t in ticker_input.split(",")]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description=f"Running backtest for {date}...", total=None)
            results = bt_engine.run_backtest(tickers, bt_date)
        
        if "error" in results:
            rprint(f"[red]Backtest failed: {results['error']}[/red]")
            return
            
        rprint(Panel(f"[bold blue]Backtest Results for {date}[/bold blue]"))
        rprint(f"Tickers analyzed: {results['tickers_count']}")
        rprint(f"Win Rate: [bold]{results['win_rate']:.2%}[/bold]")
        rprint(f"Avg Return: [bold]{results['avg_return']:.2%}[/bold]")
        rprint(f"Avg Extension: [bold]{results['avg_extension']:.2%}[/bold]")

        if results.get('catalyst_metrics'):
            cm = results['catalyst_metrics']
            rprint(Panel(
                f"Tickers with Catalyst: {cm['count']}\n"
                f"Win Rate: [bold]{cm['win_rate']:.2%}[/bold]\n"
                f"Avg Return: [bold]{cm['avg_return']:.2%}[/bold]",
                title="[bold green]Catalyst Performance[/bold green]"
            ))
        
        table = Table(title="Backtest Details", show_header=True)
        table.add_column("Ticker")
        table.add_column("Max Extension")
        table.add_column("Max Drawdown")
        table.add_column("Return")
        table.add_column("Catalyst")
        table.add_column("Result")
        
        for r in results['details']:
            res_color = "green" if r['return'] > 0 else "red"
            cat_str = "[green]YES[/green]" if r['has_catalyst'] else "[dim]NO[/dim]"
            table.add_row(
                r['ticker'],
                f"{r['extension']:.2%}",
                f"{r['max_drawdown']:.2%}",
                f"[{res_color}]{r['return']:+.2%}[/{res_color}]",
                cat_str,
                "[green]WIN[/green]" if r['return'] > 0 else "[red]LOSS[/red]"
            )
        console.print(table)
        return

    if live_loop:
        import asyncio
        from rich.live import Live
        
        def generate_table(snapshot):
            table = Table(title=f"Live Momentum Scanner - {snapshot.timestamp.strftime('%H:%M:%S')}", show_header=True, header_style="bold green")
            table.add_column("Ticker", style="cyan")
            table.add_column("Score", justify="right", style="bold")
            table.add_column("Class", justify="center")
            table.add_column("Price", justify="right")
            table.add_column("% Chg", justify="right")
            table.add_column("RelVol", justify="right")
            table.add_column("VWAP Dist", justify="right")
            
            for item in snapshot.runners:
                score_color = "green" if item.score >= 70 else "yellow" if item.score >= 40 else "white"
                class_color = "bold green" if item.classification == "Strong Runner" else "yellow" if item.classification == "Developing Runner" else "dim"
                table.add_row(
                    item.ticker, f"[{score_color}]{item.score:.1f}[/{score_color}]",
                    f"[{class_color}]{item.classification}[/{class_color}]",
                    f"${item.price:.2f}", f"{item.pct_change:+.2f}%", 
                    f"{item.relative_volume:.2f}x", f"{item.vwap_dist:+.2f}%"
                )
            return table

        async def run_loop():
            with Live(generate_table(service.get_runners()), refresh_per_second=1) as live:
                while True:
                    await asyncio.sleep(60) # Poll every 60s
                    snapshot = service.get_runners()
                    live.update(generate_table(snapshot))
        
        try:
            asyncio.run(run_loop())
        except KeyboardInterrupt:
            rprint("\n[yellow]Live scan stopped.[/yellow]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Scanning for {mode} runners...", total=None)
        snapshot = service.get_runners(mode=mode, top_n=top_n)
    
    if json_out:
        rprint(snapshot.model_dump_json(indent=2))
        return
        
    if csv_out:
        import pandas as pd
        df = pd.DataFrame([r.model_dump() for r in snapshot.runners])
        filename = f"runners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        rprint(f"[green]Exported to {filename}[/green]")
        return

    if snapshot.runners:
        table = Table(title=f"Top {mode.capitalize()} Runners", show_header=True, header_style="bold green")
        table.add_column("Ticker", style="cyan")
        table.add_column("Score", justify="right", style="bold")
        table.add_column("Class", justify="center")
        table.add_column("Price", justify="right")
        table.add_column("% Chg", justify="right")
        table.add_column("RelVol", justify="right")
        table.add_column("Gap%", justify="right")
        table.add_column("VWAP Dist", justify="right")
        table.add_column("Vol Acc", justify="right")
        
        for item in snapshot.runners:
            score_color = "green" if item.score >= 70 else "yellow" if item.score >= 40 else "white"
            class_color = "bold green" if item.classification == "Strong Runner" else "yellow" if item.classification == "Developing Runner" else "dim"
            
            table.add_row(
                item.ticker, 
                f"[{score_color}]{item.score:.1f}[/{score_color}]",
                f"[{class_color}]{item.classification}[/{class_color}]",
                f"${item.price:.2f}", 
                f"{item.pct_change:+.2f}%", 
                f"{item.relative_volume:.2f}x",
                f"{item.gap_pct:+.2f}%",
                f"{item.vwap_dist:+.2f}%",
                f"{item.volume_acceleration:.2f}x"
            )
        console.print(table)
        rprint(f"\n[dim]Analyzed {snapshot.universe_size} stocks. Snapshot at {snapshot.timestamp.strftime('%H:%M:%S')}[/dim]")
    else:
        rprint("[yellow]No runners detected matching filters.[/yellow]")

if __name__ == "__main__":
    app()
