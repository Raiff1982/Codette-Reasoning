from transformers import pipeline

class EnhancedSentimentAnalyzer:
    """Advanced sentiment analysis with additional techniques"""
    def __init__(self):
        self.sentiment_pipeline = pipeline('sentiment-analysis')

    def analyze(self, text: str) -> dict[str, any]:
        """Analyze sentiment with advanced techniques"""
        analysis = self.sentiment_pipeline(text)
        return analysis[0]

    def detailed_analysis(self, text: str) -> dict[str, any]:
        """Provide a more detailed sentiment analysis"""
        scores = self.sentiment_pipeline(text)[0]
        if scores['label'] == 'POSITIVE':
            sentiment = "Positive"
        elif scores['label'] == 'NEGATIVE':
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        return {
            "scores": scores,
            "sentiment": sentiment
        }