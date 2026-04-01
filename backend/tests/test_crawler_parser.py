"""Tests for the crawler log parser — identifies AI bots from server logs."""

from app.services.analytics.crawler_parser import (
    CrawlerType,
    identify_crawler,
    parse_combined_log_line,
    parse_cloudfront_log_line,
    parse_log_lines,
)


class TestIdentifyCrawler:
    def test_gptbot(self):
        ua = "Mozilla/5.0 AppleWebKit/537.36 (compatible; GPTBot/1.0; +https://openai.com/gptbot)"
        assert identify_crawler(ua) == CrawlerType.GPTBOT

    def test_claudebot(self):
        ua = "ClaudeBot/1.0; +https://www.anthropic.com/clwadebot"
        assert identify_crawler(ua) == CrawlerType.CLAUDEBOT

    def test_anthropic_ai(self):
        ua = "anthropic-ai (+https://www.anthropic.com)"
        assert identify_crawler(ua) == CrawlerType.CLAUDEBOT

    def test_perplexitybot(self):
        ua = "PerplexityBot/1.0"
        assert identify_crawler(ua) == CrawlerType.PERPLEXITYBOT

    def test_googlebot(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        assert identify_crawler(ua) == CrawlerType.GOOGLEBOT

    def test_google_extended(self):
        ua = "Mozilla/5.0 (compatible; Google-Extended)"
        assert identify_crawler(ua) == CrawlerType.GOOGLEBOT

    def test_bingbot(self):
        ua = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
        assert identify_crawler(ua) == CrawlerType.BINGBOT

    def test_metabot(self):
        ua = "meta-externalagent/1.0 (+https://developers.facebook.com)"
        assert identify_crawler(ua) == CrawlerType.METABOT

    def test_bytespider(self):
        ua = "Mozilla/5.0 (compatible; Bytespider)"
        assert identify_crawler(ua) == CrawlerType.BYTESPIDER

    def test_unknown_browser(self):
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/120.0"
        assert identify_crawler(ua) == CrawlerType.UNKNOWN


class TestParseCombinedLog:
    def test_gptbot_log_line(self):
        line = '66.249.66.1 - - [29/Mar/2026:10:00:00 +0000] "GET /api/products HTTP/1.1" 200 12345 "-" "GPTBot/1.0"'
        result = parse_combined_log_line(line)
        assert result is not None
        assert result["crawler_type"] == CrawlerType.GPTBOT
        assert result["ip_address"] == "66.249.66.1"
        assert result["request_path"] == "/api/products"
        assert result["status_code"] == 200
        assert result["response_size_bytes"] == 12345

    def test_normal_browser_skipped(self):
        line = '192.168.1.1 - - [29/Mar/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 5000 "-" "Mozilla/5.0 Chrome/120"'
        result = parse_combined_log_line(line)
        assert result is None

    def test_claudebot_log_line(self):
        line = '35.192.0.1 - - [29/Mar/2026:11:30:00 +0000] "GET /blog/article HTTP/1.1" 200 8000 "-" "ClaudeBot/1.0"'
        result = parse_combined_log_line(line)
        assert result is not None
        assert result["crawler_type"] == CrawlerType.CLAUDEBOT

    def test_malformed_line(self):
        result = parse_combined_log_line("not a log line")
        assert result is None


class TestParseCloudFrontLog:
    def test_gptbot_cloudfront(self):
        line = "2026-03-29\t10:00:00\tLAX1\t12345\t66.249.66.1\tGET\texample.com\t/products\t200\t-\tGPTBot/1.0\t-\t-\tHit\treq123"
        result = parse_cloudfront_log_line(line)
        assert result is not None
        assert result["crawler_type"] == CrawlerType.GPTBOT

    def test_comment_line_skipped(self):
        result = parse_cloudfront_log_line("#Version: 1.0")
        assert result is None


class TestParseLogLines:
    def test_mixed_lines(self):
        lines = [
            '66.249.66.1 - - [29/Mar/2026:10:00:00 +0000] "GET /a HTTP/1.1" 200 100 "-" "GPTBot/1.0"',
            '192.168.1.1 - - [29/Mar/2026:10:00:01 +0000] "GET /b HTTP/1.1" 200 200 "-" "Chrome/120"',
            '35.192.0.1 - - [29/Mar/2026:10:00:02 +0000] "GET /c HTTP/1.1" 200 300 "-" "ClaudeBot/1.0"',
        ]
        results = parse_log_lines(lines, "combined")
        assert len(results) == 2
        assert results[0]["crawler_type"] == CrawlerType.GPTBOT
        assert results[1]["crawler_type"] == CrawlerType.CLAUDEBOT
