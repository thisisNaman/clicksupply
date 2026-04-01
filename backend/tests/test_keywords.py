"""Tests for keyword extraction service."""

from app.services.analytics.keywords import (
    extract_keywords,
    extract_keywords_with_sentiment,
    extract_ngrams,
)


class TestExtractKeywords:
    def test_basic_extraction(self):
        texts = [
            "Zerodha is the best trading platform in India",
            "Zerodha offers zero brokerage on equity delivery trades",
            "Groww and Zerodha are the top fintech apps",
        ]
        result = extract_keywords(texts, top_n=5)
        assert len(result) > 0
        words = [r["word"] for r in result]
        assert "zerodha" in words

    def test_stopwords_filtered(self):
        texts = ["the is a an and but or for"]
        result = extract_keywords(texts, top_n=10)
        assert len(result) == 0

    def test_min_word_length(self):
        texts = ["go to do be we he it"]
        result = extract_keywords(texts, top_n=10, min_word_length=3)
        assert len(result) == 0

    def test_frequency_calculation(self):
        texts = ["apple apple apple banana banana cherry"]
        result = extract_keywords(texts, top_n=3)
        assert result[0]["word"] == "apple"
        assert result[0]["count"] == 3
        assert result[1]["word"] == "banana"
        assert result[1]["count"] == 2

    def test_empty_input(self):
        result = extract_keywords([], top_n=10)
        assert result == []

    def test_none_in_list(self):
        result = extract_keywords([None, "", "hello world testing"], top_n=5)
        assert len(result) > 0


class TestExtractKeywordsWithSentiment:
    def test_sentiment_bias(self):
        texts_with_sent = [
            ("zerodha is excellent and amazing", "positive"),
            ("zerodha is excellent and great", "positive"),
            ("zerodha has some problems", "negative"),
        ]
        result = extract_keywords_with_sentiment(texts_with_sent, top_n=5)
        zerodha = next((r for r in result if r["word"] == "zerodha"), None)
        assert zerodha is not None
        assert zerodha["sentiment_bias"] == "positive"


class TestExtractNgrams:
    def test_bigrams(self):
        texts = [
            "stock trading platform for beginners",
            "best stock trading app in india",
        ]
        result = extract_ngrams(texts, n=2, top_n=5)
        assert len(result) > 0
        ngrams = [r["ngram"] for r in result]
        assert "stock trading" in ngrams

    def test_empty_input(self):
        result = extract_ngrams([], n=2, top_n=5)
        assert result == []
