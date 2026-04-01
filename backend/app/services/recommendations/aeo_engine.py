"""
AEO Recommendation Engine — Audits web pages and generates optimization recommendations.

Implements the rules from research/03_AEO_Recommendation_Engine.md:
- Inverted Pyramid (Answer-First) content structure
- Semantic chunking (200-400 word sections)
- Schema markup (JSON-LD) generation
- llms.txt readiness
- E-E-A-T and third-party validation scoring
"""

import json
import re
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from app.schemas.schemas import AEOAuditResult, AEORecommendation
from app.services.llm.gateway import ModelTier, llm_gateway

logger = structlog.get_logger()


class AEORecommendationEngine:
    """Audits pages for AEO readiness and generates actionable recommendations."""

    async def audit_page(self, url: str) -> AEOAuditResult:
        """Full AEO audit of a web page."""
        html = await self._fetch_page(url)
        if not html:
            return AEOAuditResult(
                url=url, score=0, recommendations=[
                    AEORecommendation(
                        category="technical", severity="critical",
                        title="Page unreachable",
                        description="Could not fetch the page",
                        action="Ensure the URL is accessible",
                    )
                ], schema_suggestions=None, llms_txt_content=None,
            )

        soup = BeautifulSoup(html, "html.parser")
        recommendations = []
        score = 100.0

        # 1. Content Structure Analysis
        struct_recs, struct_penalty = self._analyze_content_structure(soup)
        recommendations.extend(struct_recs)
        score -= struct_penalty

        # 2. Schema Markup Analysis
        schema_recs, schema_penalty, schema_suggestions = self._analyze_schema(soup, url)
        recommendations.extend(schema_recs)
        score -= schema_penalty

        # 3. Technical GEO Analysis
        tech_recs, tech_penalty = self._analyze_technical(soup, url)
        recommendations.extend(tech_recs)
        score -= tech_penalty

        # 4. Trust Signals (E-E-A-T)
        trust_recs, trust_penalty = self._analyze_trust_signals(soup)
        recommendations.extend(trust_recs)
        score -= trust_penalty

        # 5. Generate llms.txt
        llms_txt = self._generate_llms_txt(soup, url)

        return AEOAuditResult(
            url=url,
            score=max(0, round(score, 1)),
            recommendations=recommendations,
            schema_suggestions=schema_suggestions,
            llms_txt_content=llms_txt,
        )

    def _analyze_content_structure(self, soup: BeautifulSoup) -> tuple[list, float]:
        recs = []
        penalty = 0.0

        # Check for answer-first pattern (direct answer within first 60 words after H2/H3)
        headings = soup.find_all(["h2", "h3"])
        if not headings:
            recs.append(AEORecommendation(
                category="content_structure", severity="critical",
                title="No H2/H3 headings found",
                description="LLMs rely on heading hierarchy to extract passage-level answers",
                action="Add clear H2/H3 headings with question-format text",
            ))
            penalty += 20

        # Check paragraph length after headings (inverted pyramid)
        for h in headings[:5]:
            next_p = h.find_next_sibling("p")
            if next_p:
                words = len(next_p.get_text().split())
                if words > 80:
                    recs.append(AEORecommendation(
                        category="content_structure", severity="warning",
                        title=f"Answer buried after '{h.get_text()[:50]}'",
                        description=f"First paragraph has {words} words. LLMs prefer 40-60 word direct answers",
                        action="Place a concise 40-60 word answer immediately after the heading",
                    ))
                    penalty += 5

        # Check for structured content (lists, tables)
        lists = soup.find_all(["ul", "ol"])
        tables = soup.find_all("table")
        if not lists and not tables:
            recs.append(AEORecommendation(
                category="content_structure", severity="warning",
                title="No structured content found",
                description="LLMs retrieve structured text (lists, tables) 40% more reliably",
                action="Add bullet points, numbered lists, or comparison tables",
            ))
            penalty += 10

        return recs, penalty

    def _analyze_schema(self, soup: BeautifulSoup, url: str) -> tuple[list, float, dict]:
        recs = []
        penalty = 0.0

        # Find existing JSON-LD
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        existing_types = set()
        for s in scripts:
            try:
                data = json.loads(s.string)
                if isinstance(data, dict):
                    existing_types.add(data.get("@type", ""))
                elif isinstance(data, list):
                    for item in data:
                        existing_types.add(item.get("@type", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        suggestions = {}

        if "FAQPage" not in existing_types:
            recs.append(AEORecommendation(
                category="schema_markup", severity="critical",
                title="Missing FAQPage schema",
                description="Pages with FAQPage schema achieve 2.7x higher AI citation rates",
                action="Add FAQPage JSON-LD schema for Q&A content",
            ))
            penalty += 15
            suggestions["FAQPage"] = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "[Your question here]",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "[Direct answer here]",
                        },
                    }
                ],
            }

        if "Organization" not in existing_types and "Person" not in existing_types:
            recs.append(AEORecommendation(
                category="schema_markup", severity="warning",
                title="Missing Organization/Person schema",
                description="Entity schemas help AI establish authoritativeness",
                action="Add Organization JSON-LD with sameAs links to Wikidata, LinkedIn",
            ))
            penalty += 10
            domain = urlparse(url).netloc
            suggestions["Organization"] = {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "[Organization Name]",
                "url": f"https://{domain}",
                "sameAs": ["https://www.linkedin.com/company/...", "https://www.wikidata.org/wiki/..."],
            }

        if "Article" not in existing_types:
            suggestions["Article"] = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "[Title]",
                "author": {"@type": "Person", "name": "[Author]"},
                "datePublished": "[ISO Date]",
                "dateModified": "[ISO Date]",
            }

        return recs, penalty, suggestions if suggestions else None

    def _analyze_technical(self, soup: BeautifulSoup, url: str) -> tuple[list, float]:
        recs = []
        penalty = 0.0

        # Check for heavy JS that may block AI crawlers
        scripts = soup.find_all("script", src=True)
        if len(scripts) > 20:
            recs.append(AEORecommendation(
                category="technical", severity="warning",
                title=f"Heavy JavaScript ({len(scripts)} scripts)",
                description="AI crawlers like GPTBot have limited JS execution. Complex DOM rendering blocks passage extraction",
                action="Ensure critical content is server-rendered, not client-only JS",
            ))
            penalty += 10

        # Check meta robots
        meta_robots = soup.find("meta", {"name": "robots"})
        if meta_robots:
            content = meta_robots.get("content", "")
            if "noindex" in content or "nofollow" in content:
                recs.append(AEORecommendation(
                    category="technical", severity="critical",
                    title="Robots meta blocks indexing",
                    description=f"Meta robots: {content}. AI crawlers respect these directives",
                    action="Remove noindex/nofollow if you want AI visibility",
                ))
                penalty += 25

        # Check for canonical
        canonical = soup.find("link", {"rel": "canonical"})
        if not canonical:
            recs.append(AEORecommendation(
                category="technical", severity="info",
                title="No canonical tag found",
                description="Canonical tags help AI engines identify the primary version of content",
                action="Add a canonical link tag",
            ))
            penalty += 3

        return recs, penalty

    def _analyze_trust_signals(self, soup: BeautifulSoup) -> tuple[list, float]:
        recs = []
        penalty = 0.0

        text = soup.get_text().lower()

        # Check for author attribution
        author_patterns = ["written by", "author:", "by ", "published by"]
        has_author = any(p in text for p in author_patterns)
        if not has_author:
            recs.append(AEORecommendation(
                category="trust", severity="warning",
                title="No author attribution found",
                description="E-E-A-T: AI engines weigh content with clear authorship more heavily",
                action="Add visible author name, credentials, and link to author profile",
            ))
            penalty += 8

        # Check for external citations/references
        links = soup.find_all("a", href=True)
        external_links = [
            l for l in links
            if l["href"].startswith("http") and not l["href"].startswith("#")
        ]
        if len(external_links) < 3:
            recs.append(AEORecommendation(
                category="trust", severity="info",
                title="Few external references",
                description="LLMs prioritize third-party consensus. Linking to authoritative sources improves citation likelihood",
                action="Add references to industry reports, studies, or authoritative domains",
            ))
            penalty += 5

        return recs, penalty

    def _generate_llms_txt(self, soup: BeautifulSoup, url: str) -> str:
        """Generate an llms.txt file content based on page structure."""
        domain = urlparse(url).netloc
        title = soup.find("title")
        title_text = title.get_text().strip() if title else domain

        meta_desc = soup.find("meta", {"name": "description"})
        desc = meta_desc.get("content", "") if meta_desc else ""

        headings = soup.find_all(["h1", "h2"])
        sections = []
        for h in headings[:10]:
            sections.append(f"- [{h.get_text().strip()}]({url}#{h.get('id', '')})")

        return f"""# {title_text}

> {desc}

## Core Pages

{chr(10).join(sections) if sections else '- [Homepage](' + url + ')'}

## Contact

- [Website]({url})
"""

    async def _fetch_page(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "ClickSupply-AEO-Auditor/1.0"})
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.error("page_fetch_failed", url=url, error=str(e))
            return None


aeo_engine = AEORecommendationEngine()
