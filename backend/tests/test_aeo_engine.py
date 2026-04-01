"""Tests for AEO Recommendation Engine — page audit logic."""

import pytest
from app.services.recommendations.aeo_engine import AEORecommendationEngine


@pytest.fixture
def engine():
    return AEORecommendationEngine()


class TestContentStructure:
    def test_no_headings_flagged(self, engine):
        from bs4 import BeautifulSoup
        html = "<html><body><p>Just a paragraph without headings.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty = engine._analyze_content_structure(soup)
        assert any(r.title == "No H2/H3 headings found" for r in recs)
        assert penalty >= 20

    def test_good_structure_no_penalty(self, engine):
        from bs4 import BeautifulSoup
        html = """<html><body>
            <h2>What is AEO?</h2>
            <p>AEO stands for Answer Engine Optimization, a method to improve brand visibility in AI search engines.</p>
            <ul><li>Item 1</li><li>Item 2</li></ul>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty = engine._analyze_content_structure(soup)
        assert penalty < 20  # Should have low penalty


class TestSchemaAnalysis:
    def test_missing_faqpage_schema(self, engine):
        from bs4 import BeautifulSoup
        html = "<html><body><h2>FAQ</h2></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty, suggestions = engine._analyze_schema(soup, "https://example.com")
        assert any("FAQPage" in r.title for r in recs)
        assert "FAQPage" in suggestions

    def test_existing_faqpage_no_flag(self, engine):
        from bs4 import BeautifulSoup
        html = '''<html><body>
            <script type="application/ld+json">{"@type": "FAQPage", "@context": "https://schema.org"}</script>
        </body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty, suggestions = engine._analyze_schema(soup, "https://example.com")
        assert not any("FAQPage" in r.title for r in recs)


class TestTrustSignals:
    def test_no_author_flagged(self, engine):
        from bs4 import BeautifulSoup
        html = "<html><body><p>Content without author.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty = engine._analyze_trust_signals(soup)
        assert any("author" in r.title.lower() for r in recs)

    def test_author_present(self, engine):
        from bs4 import BeautifulSoup
        html = "<html><body><p>Written by John Doe, expert in AI.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        recs, penalty = engine._analyze_trust_signals(soup)
        assert not any("author" in r.title.lower() for r in recs)


class TestLlmsTxt:
    def test_generates_llms_txt(self, engine):
        from bs4 import BeautifulSoup
        html = """<html><head><title>My Site</title>
            <meta name="description" content="A great site">
        </head><body>
            <h1>Welcome</h1><h2>About</h2>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = engine._generate_llms_txt(soup, "https://example.com")
        assert "# My Site" in result
        assert "A great site" in result
