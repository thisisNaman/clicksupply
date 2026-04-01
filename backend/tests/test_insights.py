"""Tests for insights and export endpoint imports + schema validation."""

from app.schemas.schemas import (
    SentimentResponse,
    SentimentByEngine,
    KeywordItem,
    SentimentTrend,
    CitationResponse,
    CitationDomain,
    TrendsResponse,
    TrendPoint,
    PlatformsResponse,
    PlatformStat,
    BenchmarkResponse,
    BenchmarkMetrics,
)


class TestSentimentSchemas:
    def test_sentiment_by_engine(self):
        s = SentimentByEngine(
            engine="chatgpt",
            positive_pct=60.5,
            neutral_pct=25.0,
            negative_pct=14.5,
            total_responses=100,
        )
        assert s.engine == "chatgpt"
        assert s.positive_pct == 60.5

    def test_keyword_item(self):
        k = KeywordItem(word="zerodha", count=42, sentiment_bias="positive")
        assert k.word == "zerodha"

    def test_sentiment_response(self):
        r = SentimentResponse(
            per_engine=[],
            top_keywords=[],
            trend=[],
        )
        assert r.per_engine == []


class TestCitationSchemas:
    def test_citation_domain(self):
        c = CitationDomain(domain="zerodha.com", count=15, engines=["chatgpt", "gemini"])
        assert len(c.engines) == 2

    def test_citation_response(self):
        r = CitationResponse(top_domains=[], total_citations=0, unique_domains=0)
        assert r.total_citations == 0


class TestTrendsSchemas:
    def test_trend_point(self):
        t = TrendPoint(
            date="2025-01-01",
            visibility_score=72.5,
            mention_count=45,
            avg_position=1.8,
            sentiment_positive_pct=65.0,
        )
        assert t.visibility_score == 72.5

    def test_trends_response(self):
        r = TrendsResponse(series=[])
        assert r.series == []


class TestPlatformSchemas:
    def test_platform_stat(self):
        p = PlatformStat(
            engine="chatgpt",
            visibility_score=80.0,
            avg_position=1.5,
            mention_rate=75.0,
            sentiment_positive_pct=65.0,
            citation_count=120,
        )
        assert p.citation_count == 120


class TestBenchmarkSchemas:
    def test_benchmark_metrics(self):
        m = BenchmarkMetrics(
            name="Zerodha",
            domain="zerodha.com",
            avg_som=72.0,
            avg_position=1.8,
            mention_count=350,
            sentiment_positive_pct=68.5,
        )
        assert m.name == "Zerodha"

    def test_benchmark_response(self):
        r = BenchmarkResponse(
            brand=BenchmarkMetrics(
                name="Zerodha",
                avg_som=72.0,
                avg_position=1.8,
                mention_count=350,
                sentiment_positive_pct=68.5,
            ),
            competitors=[],
            rankings={"som_rank": 1, "total_entities": 1},
        )
        assert r.rankings["som_rank"] == 1
