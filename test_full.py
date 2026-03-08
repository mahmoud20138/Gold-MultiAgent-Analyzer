"""Test full analysis with Azure AI sentiment."""
import sys
sys.path.insert(0, '.')

from agents.orchestrator import GoldTradingOrchestrator

print('Starting FULL analysis with Azure AI sentiment...')
print('=' * 60)

orch = GoldTradingOrchestrator()

# Run FULL analysis WITH sentiment
result = orch.analyze('XAUUSDm', include_sentiment=True)
orch.disconnect()

# Show sentiment
sentiment = result.get('sentiment', {})
print()
print('=' * 60)
print('SENTIMENT ANALYSIS (Azure AI - Llama 3.1 8B)')
print('=' * 60)
print(f"Status: {sentiment.get('status')}")
print(f"Score: {sentiment.get('score')}/100")
print(f"Direction: {sentiment.get('direction')}")
print(f"Conviction: {sentiment.get('conviction')}")
print(f"Method: {sentiment.get('method')}")
print()
if sentiment.get('analysis'):
    print('Analysis:')
    print(sentiment.get('analysis')[:500])

# Show recommendation
rec = result.get('recommendation', {})
print()
print('=' * 60)
print('TRADE RECOMMENDATION')
print('=' * 60)
print(f"Direction: {rec.get('direction')}")
print(f"Confidence: {rec.get('confidence_score')}/100")
print(f"Grade: {rec.get('trade_grade')}")
print(f"Entry: {rec.get('entry_price')}")
print(f"Stop Loss: {rec.get('stop_loss')}")
print(f"Take Profit 1: {rec.get('take_profit_1')}")
print(f"R:R: {rec.get('risk_reward_ratio')}")
print(f"Action: {rec.get('trade_action')}")

print()
print(f"Elapsed: {result.get('elapsed_seconds')}s")
