import litellm
import json
import re
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
            "temperature": 0.0,  # deterministic output for analysis tasks
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_format:
            kwargs["response_format"] = response_format
            
        return litellm.completion(**kwargs)

    def _get_content(self, response):
        """Extracts content and removes reasoning tags."""
        content = response.choices[0].message.content
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    def _parse_json_response(self, response):
        """
        Extracts and parses JSON from the LLM response content.
        Handles reasoning tags, markdown blocks, and provides regex-based fallbacks.
        """
        content = response.choices[0].message.content
        
        # 1. Remove <think> tags (common in reasoning models)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        # 2. Try to find a JSON block in markdown
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. Try to find anything between the first { and last }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end >= start:
            try:
                return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                pass
        
        # 4. Regex-based extraction fallback for key fields
        # This helps if the LLM didn't return valid JSON but the fields are there in text
        extracted = {}
        fields = [
            "role", "opinion", "recommendation", 
            "conviction_score", "risk_adjusted_rating", 
            "agreement_index", "position_size_suggestion"
        ]
        for field in fields:
            # Match "field": "value", field: value, etc.
            pattern = fr'["\']?{field}["\']?\s*[:=]\s*(?:"([^"]*)"|\'([^\']*)\'|([^,}}\n]+))'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                val = match.group(1) or match.group(2) or match.group(3)
                if val:
                    try:
                        # Clean up value and try to convert to float if applicable
                        val = val.strip().rstrip(',').rstrip('}').strip('"\'')
                        if field in ["conviction_score", "risk_adjusted_rating", "agreement_index", "position_size_suggestion"]:
                            # Try to extract the first number found in the value
                            num_match = re.search(r'(\d+\.?\d*)', val)
                            if num_match:
                                extracted[field] = float(num_match.group(1))
                        else:
                            extracted[field] = val
                    except:
                        extracted[field] = val
        
        # List fields for FinalDecision
        for field in ["primary_drivers", "key_risks"]:
            list_match = re.search(fr'["\']?{field}["\']?\s*[:=]\s*\[(.*?)\]', content, re.DOTALL | re.IGNORECASE)
            if list_match:
                items = re.findall(r'["\']([^"\']+)["\']', list_match.group(1))
                if not items:
                    # Try splitting by comma if no quotes
                    items = [i.strip().strip('"\'') for i in list_match.group(1).split(',') if i.strip()]
                extracted[field] = items

        if extracted:
            if "opinion" not in extracted:
                extracted["opinion"] = content
            return extracted

        # 5. Fallback to direct load
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Last resort: put everything in opinion
            return {"opinion": content}

    def analyze_health(self, financials: CompanyFinancials) -> str:
        prompt = f"""
        Analyze the company health based on the following financial data:
        {financials.model_dump_json(indent=2)}
        
        Provide a concise summary of the company health.
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return self._get_content(response)

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
        return self._get_content(response)

    def analyze_sentiment(self, news: List[NewsItem]) -> str:
        news_details = "\n".join([f"- [{item.publisher}] {item.title} (Source: {item.link})" for item in news[:20]])
        prompt = f"""
        Based on the following news and social media titles from various sources (Reuters, WSJ, Bloomberg, MarketWatch, and X), 
        analyze the social sentiment and key data for the stock.
        
        You MUST base your analysis ONLY on the provided news titles. Do not hallucinate external events.
        Include references to specific publishers when citing data.
        
        Emit a response of 'Good' or 'Bad' for overall sentiment, and provide a summary of bullish and bearish points.
        Pay special attention to social sentiment if X (Twitter) sources are present.
        
        News & Social Feed:
        {news_details}
        
        Format:
        Sentiment: [Good/Bad]
        Sources Used: [List the publishers found in the feed]
        Social Sentiment: [Briefly describe the vibe on social media if available]
        Summary: [Detailed bullish and bearish summary based on the sources]
        Reasoning: [Explain your logic based on the frequency and weight of sources]
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return self._get_content(response)

    def get_trader_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Trader. Evaluate the following technical and quantitative data for {data.get('ticker')}:
        
        Technical Structure: {json.dumps(data.get('technical_levels'), indent=2)}
        Relative Strength: {json.dumps(data.get('relative_strength'), indent=2)}
        Monte Carlo Upside: {json.dumps(data.get('monte_carlo'), indent=2)}
        Market Regime: {json.dumps(data.get('market_regime'), indent=2)}
        Sentiment Analysis: {data.get('sentiment_news_analysis')}
        
        Evaluate the technical structure, relative strength, Monte Carlo upside probability, and regime alignment.
        Base your opinion ONLY on the provided data. Do not hallucinate or use external knowledge.
        
        Respond ONLY in JSON format:
        {{
            "role": "Trader",
            "opinion": "Detailed reasoning based on technicals, regime, and sentiment sources. Be specific about numbers and levels.",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**self._parse_json_response(response))

    def get_analyst_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Financial Analyst. Evaluate the following fundamental and comparative data for {data.get('ticker')}:
        
        Company Health Summary: {data.get('health_summary')}
        Market Value Analysis: {data.get('market_value_analysis')}
        Financials: {json.dumps(data.get('financials'), indent=2)}
        Relative Strength (Growth vs Peers): {json.dumps(data.get('relative_strength'), indent=2)}
        Recent News context: {data.get('sentiment_news_analysis')}
        
        Evaluate company health, valuation, growth vs peers, and sector positioning.
        Ensure your analysis is grounded in the specific numbers provided. Do not hallucinate.
        
        Respond ONLY in JSON format:
        {{
            "role": "Analyst",
            "opinion": "Detailed fundamental reasoning. Compare the health summary with the market valuation and peer data.",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**self._parse_json_response(response))

    def get_risk_manager_opinion(self, data: dict) -> JudgeOpinion:
        prompt = f"""
        You are a Professional Risk Manager. Evaluate the following risk and impact data for {data.get('ticker')}:
        
        Risk Metrics: {json.dumps(data.get('risk_metrics'), indent=2)}
        Monte Carlo Downside: {json.dumps(data.get('monte_carlo'), indent=2)}
        Portfolio Impact: {json.dumps(data.get('portfolio_impact'), indent=2)}
        Market Regime Multiplier: {json.dumps(data.get('market_regime'), indent=2)}
        News-based Risks: {data.get('sentiment_news_analysis')}
        
        Evaluate RiskMetrics, Monte Carlo downside probability, portfolio impact, regime risk multiplier, and drawdown profile.
        Identify tail risks and provide a conservative assessment. Do not hallucinate risks not supported by data.
        
        Respond ONLY in JSON format:
        {{
            "role": "Risk Manager",
            "opinion": "Detailed risk assessment reasoning. Focus on VaR, drawdown, and correlation risks.",
            "recommendation": "Buy/Hold/Sell"
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return JudgeOpinion(**self._parse_json_response(response))

    def resolve_final_decision(self, opinions: List[JudgeOpinion], data: dict) -> FinalDecision:
        opinions_data = [o.model_dump() for o in opinions]
        prompt = f"""
        You are the Chief Investment Officer. Your goal is to review the reports from the Trader, Analyst, and Risk Manager and provide a final, unified decision.
        
        STRICT LOGIC RUBRIC:
        1. Risk Priority: If Risk Manager recommendation is 'Sell' AND 1Y Volatility > 0.50, the final decision MUST be 'Sell' or 'Hold'. NEVER 'Buy'.
        2. Valuation Cap: If Analyst says 'Overvalued' AND P/E > 100, the final decision MUST NOT be 'Buy' unless the Trader report confirms the price has broken above all resistance levels.
        3. Conflict Resolution: 
           - If Market Regime is 'Bullish Expansion', give 60% weight to the Trader's momentum.
           - If Market Regime is 'Bearish' or 'Volatile', give 60% weight to the Risk Manager's caution.
        4. Position Sizing: Use the 'Suggested Position Size (Kelly capped)' as a maximum. Reduce this size if the Risk Manager flags high correlation or drawdown risks.
        
        INPUT DATA:
        {json.dumps(opinions_data, indent=2)}
        
        MARKET CONTEXT:
        Regime: {data.get('market_regime')}
        Volatility: {data.get('volatility_1y')}
        Deterministic Position Limit: {data.get('deterministic_analysis', {}).get('final_suggested_size')}
        
        TASK:
        1. Conduct a logic audit: Check the input against the 4 logic rules above.
        2. Resolve conflicts between the three judges.
        3. Output the final decision in JSON.
        
        Respond ONLY in this JSON format:
        {{
            "logic_audit": "Step-by-step reasoning showing how you applied the Logic Rubric",
            "recommendation": "Buy/Hold/Sell",
            "conviction_score": (number between 0-100),
            "risk_adjusted_rating": (number between 0-5.0),
            "agreement_index": (number between 0-1.0),
            "position_size_suggestion": (number between 0.0-1.0),
            "primary_drivers": ["driver 1", "driver 2", etc],
            "key_risks": ["risk 1", "risk 2", etc]
        }}
        """
        response = self._get_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return FinalDecision(**self._parse_json_response(response))

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
