"""
Keyword extraction service — frequency-based keyword extraction from AI responses.

Uses stdlib Counter + stopword list. No external NLP deps.
"""

import re
from collections import Counter, defaultdict

# Extended stopword list
STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could and but or nor for yet so at by from in into "
    "of on to with as it its i me my we our you your he she they them their this "
    "that these those what which who whom how when where why all any each every no "
    "not very also just about above after again between both during few more most "
    "other some such than too up down out off over under same own here there then "
    "been being get got make made let new one two three like use used using "
    "well many much need good great best way find first look people know take "
    "help keep give think see try include including provide offer work want "
    "different available based come going sure able really time thing right "
    "even still back part long high low set top end start point place".split()
)


def extract_keywords(
    texts: list[str],
    top_n: int = 30,
    min_word_length: int = 3,
) -> list[dict]:
    """Extract top keywords from a list of text documents.

    Returns: [{"word": str, "count": int, "frequency": float}]
    """
    word_counter: Counter = Counter()
    total_words = 0

    for text in texts:
        if not text:
            continue
        words = re.findall(r"[a-zA-Z]{%d,}" % min_word_length, text.lower())
        for w in words:
            if w not in STOPWORDS:
                word_counter[w] += 1
                total_words += 1

    total_words = total_words or 1
    return [
        {
            "word": word,
            "count": count,
            "frequency": round(count / total_words * 100, 3),
        }
        for word, count in word_counter.most_common(top_n)
    ]


def extract_keywords_with_sentiment(
    texts_with_sentiment: list[tuple[str, str]],
    top_n: int = 20,
    min_word_length: int = 3,
) -> list[dict]:
    """Extract keywords with sentiment bias.

    Args:
        texts_with_sentiment: list of (text, sentiment) where sentiment is "positive"|"neutral"|"negative"

    Returns: [{"word": str, "count": int, "sentiment_bias": str}]
    """
    word_counter: Counter = Counter()
    word_sentiment: dict[str, Counter] = defaultdict(Counter)

    for text, sentiment in texts_with_sentiment:
        if not text:
            continue
        words = re.findall(r"[a-zA-Z]{%d,}" % min_word_length, text.lower())
        for w in words:
            if w not in STOPWORDS:
                word_counter[w] += 1
                word_sentiment[w][sentiment] += 1

    result = []
    for word, count in word_counter.most_common(top_n):
        bias = word_sentiment[word].most_common(1)[0][0] if word_sentiment[word] else "neutral"
        result.append({"word": word, "count": count, "sentiment_bias": bias})

    return result


def extract_ngrams(
    texts: list[str],
    n: int = 2,
    top_n: int = 20,
    min_word_length: int = 3,
) -> list[dict]:
    """Extract top n-grams from a list of texts.

    Returns: [{"ngram": str, "count": int}]
    """
    ngram_counter: Counter = Counter()

    for text in texts:
        if not text:
            continue
        words = [
            w for w in re.findall(r"[a-zA-Z]{%d,}" % min_word_length, text.lower())
            if w not in STOPWORDS
        ]
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i : i + n])
            ngram_counter[ngram] += 1

    return [
        {"ngram": ngram, "count": count}
        for ngram, count in ngram_counter.most_common(top_n)
    ]
