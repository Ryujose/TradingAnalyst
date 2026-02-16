import litellm
import json
from typing import List
from ..domain.interfaces import LLMService
from ..domain.models import (
    CompanyFinancials, NewsItem, FinalRecommendation, JudgeOpinion,
    FinalDecision, RiskMetrics, RelativeStrengthReport, MonteCarloForecast,
    MarketRegime, PortfolioImpactReport
)

class LiteLLMService(LLMService):
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.api_base = None
        
        # If it's a gemini model and no provider is specified, 
        # default to 'gemini/' (Google AI Studio) instead of 'vertex_ai/'
        if self.model.startswith("gemini-") and "/" not in self.model:
            self.model = f"gemini/{self.model}"
        
        # Support for local providers
        from ..config import Config
        if self.model.startswith("ollama/"):
            self.api_base = Config.OLLAMA_API_BASE
        elif self.model.startswith("lm_studio/"):
            # LM Studio is typically OpenAI compatible
            self.model = self.model.replace("lm_studio/", "openai/", 1)
            self.api_base = Config.LM_STUDIO_API_BASE

    def _get_completion(self, messages, response_format=None):
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_format:
            kwargs["response_format"] = response_format
            
        return litellm.completion(**kwargs)

    def analyze_health(self, financials: CompanyFinancials) -> str:
        prompt = f"""
        Analyze the company health based on the following financial data:
        {financials.model_dump_json(indent=2)}
        
        Provide a concise summary of the company health.
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_market_value(self, financials: CompanyFinancials, current_price: float) -> str:
        prompt = f"""
        Analyze if the stock value on the market is good relative to the company health.
        Current Price: {current_price}
        Financials: {financials.model_dump_json(indent=2)}
        
        Is it undervalued, overvalued, or fairly valued? Provide a brief justification.
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_sentiment(self, news: List[NewsItem]) -> str:
        news_details = "\n".join([f"- [{item.publisher}] {item.title}" for item in news[:15]])
        prompt = f"""
        Based on the following news and social media titles from various sources (including Reuters, WSJ, MarketWatch, and X), 
        analyze the social sentiment and key data for the stock.
        
        Emit a response of 'Good' or 'Bad' for overall sentiment, and provide a summary of bullish and bearish points.
        Pay special attention to social sentiment if X (Twitter) sources are present.
        
        News & Social Feed:
        {news_details}
        
        Format:
        Sentiment: [Good/Bad]
        Social Sentiment: [Briefly describe the vibe on social media if available]
        Summary: [Concise bullish and bearish summary]
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def get_trader_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Trader. Evaluate the following technical and quantitative data:
        
        Technical Structure: {json.dumps(data.get('technical_levels'), indent=2)}
        Relative Strength: {json.dumps(data.get('relative_strength'), indent=2)}
        Monte Carlo Upside: {json.dumps(data.get('monte_carlo'), indent=2)}
        Market Regime: {json.dumps(data.get('market_regime'), indent=2)}
        Sentiment: {data.get('sentiment_news_analysis')}
        
        Evaluate the technical structure, relative strength, Monte Carlo upside probability, and regime alignment.
        
        Respond ONLY in JSON format:
        {{
            "role": "Trader",
            "opinion": "your detailed reasoning here...",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**json.loads(response.choices[0].message.content))

    def get_analyst_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Financial Analyst. Evaluate the following fundamental and comparative data:
        
        Company Health Summary: {data.get('health_summary')}
        Market Value Analysis: {data.get('market_value_analysis')}
        Financials: {json.dumps(data.get('financials'), indent=2)}
        Relative Strength (Growth vs Peers): {json.dumps(data.get('relative_strength'), indent=2)}
        
        Evaluate company health, valuation, growth vs peers, and sector positioning.
        
        Respond ONLY in JSON format:
        {{
            "role": "Analyst",
            "opinion": "your detailed reasoning here...",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**json.loads(response.choices[0].message.content))

    def get_risk_manager_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Risk Manager. Evaluate the following risk and impact data:
        
        Risk Metrics: {json.dumps(data.get('risk_metrics'), indent=2)}
        Monte Carlo Downside: {json.dumps(data.get('monte_carlo'), indent=2)}
        Portfolio Impact: {json.dumps(data.get('portfolio_impact'), indent=2)}
        Market Regime Multiplier: {json.dumps(data.get('market_regime'), indent=2)}
        
        Evaluate RiskMetrics, Monte Carlo downside probability, portfolio impact, regime risk multiplier, and drawdown profile.
        
        Respond ONLY in JSON format:
        {{
            "role": "Risk Manager",
            "opinion": "your detailed reasoning here...",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**json.loads(response.choices[0].message.content))

    def resolve_final_decision(self, opinions: List[JudgeOpinion], data: dict) -> FinalDecision:
        opinions_data = [o.model_dump() for o in opinions]
        prompt = f"""
        You are the Simulated Final Decision AI. Your role is to reconcile the opinions of three experts and provide a final recommendation.
        
        Expert Opinions:
        {json.dumps(opinions_data, indent=2)}
        
        Market Context & Deterministic Scoring:
        Regime: {json.dumps(data.get('market_regime'), indent=2)}
        Deterministic Risk Score: {data.get('deterministic_risk_score')}
        Suggested Position Size (Kelly capped): {data.get('portfolio_impact', {}).get('suggested_position_size')}
        
        Tasks:
        1. Compare conviction levels.
        2. Detect disagreements.
        3. Adjust for regime multiplier.
        4. Resolve conflicts logically (e.g., If Risk Manager is strongly bearish, downgrade conviction).
        
        Respond ONLY in JSON format:
        {{
            "recommendation": "Buy/Hold/Sell",
            "conviction_score": 0-100,
            "risk_adjusted_rating": 0-5.0,
            "agreement_index": 0-1.0,
            "position_size_suggestion": 0.0-1.0,
            "primary_drivers": ["driver 1", "driver 2"],
            "key_risks": ["risk 1", "risk 2"]
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return FinalDecision(**json.loads(response.choices[0].message.content))

    def get_judge_opinions(self, data: dict) -> FinalRecommendation:
        # Legacy method for backward compatibility if needed, but we should use the new ones
        trader = self.get_trader_opinion(data)
        analyst = self.get_analyst_opinion(data)
        risk = self.get_risk_manager_opinion(data)
        
        final_rec = FinalRecommendation(
            trader_opinion=trader,
            analyst_opinion=analyst,
            risk_pro_opinion=risk,
            final_user_recommendation="See Final Decision",
            justification="Consolidated from expert judges."
        )
        return final_rec
