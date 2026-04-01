# ClickSupply: AEO Optimization & Recommendation Logic

This module defines the rules engine ClickSupply uses to audit client websites and generate actionable GEO recommendations. 

## 1. Content Architecture Rules
*   **The Inverted Pyramid (Answer-First):** The system must flag pages that bury answers. Recommendations must enforce placing a 40-60 word direct, verifiable answer immediately after an H2/H3 heading.
*   **Information Density:** Recommend replacing vague marketing copy with Markdown tables, numbered lists, and bullet points, as LLMs retrieve structured text 40% more reliably.
*   **Semantic Chunking:** Advise clients to keep sections between 200-400 words with clear semantic boundaries.

## 2. Technical GEO & Machine Readability
*   **Schema Markup Generator:** Automate the generation of deeply nested `JSON-LD` schema for clients, specifically targeting `FAQPage`, `HowTo`, `Article`, `Organization`, and `Product` schemas. Pages with `FAQPage` schema achieve 2.7x higher AI citation rates.
*   **`llms.txt` Readiness:** Provide tools to help clients generate an `llms.txt` file (a markdown-based index standard) to guide AI agents cleanly to core documentation, bypassing HTML noise.

## 3. E-E-A-T and Third-Party Validation (The Trust Layer)
LLMs prioritize third-party consensus over first-party claims. ClickSupply must analyze and recommend actions for off-site authority:
*   **The Consensus Layer:** Monitor Reddit, MouthShut, G2, and Quora. Reddit accounts for up to 46.7% of Perplexity citations and 21% of Google AIOs. 
*   **Verification Anchors:** Advise linking `Person` and `Organization` schema via `sameAs` properties to Wikidata, LinkedIn, and corporate filings (NSE/BSE) to establish a verifiable entity graph.