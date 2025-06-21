"""
Utility functions for sentiment analysis.
"""
import os
import re
import nltk
import pickle

from nltk.sentiment import SentimentIntensityAnalyzer
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences


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

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(base_dir, "sentiment_model_components")
        self.model_path = os.path.join(self.model_dir, "sentiment_model.h5")
        self.tokenizer_path = os.path.join(self.model_dir, "tokenizer.pkl")
        self.labels_path = os.path.join(self.model_dir, "sentiment_labels.pkl")

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

        # try:
        #     sentences = nltk.sent_tokenize(text)
        #     return [s.strip() for s in sentences if s.strip()]
        # except Exception:
        #     # Fallback to simple splitting
        #     # sentences = re.split(r'(?<=[.!?])\s+', text)
        #     return [s.strip() for s in sentences if s.strip()]

        return [text.strip()]

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

        # scores = self.sia.polarity_scores(text)
        try:
            self.loaded_model = load_model(self.model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

        with open(self.tokenizer_path, 'rb') as f:
            self.loaded_tokenizer = pickle.load(f)

        with open(self.labels_path, 'rb') as f:
            self.loaded_sentiment_label = pickle.load(f)

        tw = self.loaded_tokenizer.texts_to_sequences([text])
        tw = pad_sequences(tw, maxlen=200)
        prediction = int(self.loaded_model.predict(tw, verbose=0).round().item())
        predicted_label = self.loaded_sentiment_label[1][prediction]

        if predicted_label == 1:
            return 'positive'
        elif predicted_label == 0:
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
