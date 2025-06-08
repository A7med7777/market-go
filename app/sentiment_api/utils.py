"""
Utility functions for sentiment analysis.
"""
import re
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer


class SentimentAnalyzer:
    """Class to handle sentiment analysis operations."""

    def __init__(self):
        """Initialize the sentiment analyzer."""
        try:
            # Download required NLTK data if not present
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon')

        self.sia = SentimentIntensityAnalyzer()

    def split_into_sentences(self, text):
        """
        Split text into sentences.

        Args:
            text (str): The input text to split

        Returns:
            list: List of sentences
        """
        if not text or not isinstance(text, str):
            return []

        try:
            sentences = nltk.sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except Exception:
            # Fallback to simple splitting
            sentences = re.split(r'(?<=[.!?])\s+', text)
            return [s.strip() for s in sentences if s.strip()]

    def analyze_sentiment(self, text):
        """
        Analyze the sentiment of text.

        Args:
            text (str): The text to analyze

        Returns:
            str: 'positive', 'negative', or 'neutral'
        """
        if not text or not isinstance(text, str) or not text.strip():
            return 'neutral'

        scores = self.sia.polarity_scores(text)

        if scores['compound'] >= 0.05:
            return 'positive'
        elif scores['compound'] <= -0.05:
            return 'negative'
        else:
            return 'neutral'

    def process_comment(self, comment):
        """
        Process a single comment for sentiment analysis.

        Args:
            comment (str): The comment to process

        Returns:
            dict: Processed comment with sentence-level sentiment analysis
        """
        sentences = self.split_into_sentences(comment)
        sentence_analyses = []

        for sentence in sentences:
            sentiment = self.analyze_sentiment(sentence)
            sentence_analyses.append({
                "sentence": sentence,
                "sentiment": sentiment
            })

        return {
            "comment": comment,
            "sentences": sentence_analyses
        }
