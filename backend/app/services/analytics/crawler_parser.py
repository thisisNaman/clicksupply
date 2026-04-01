"""
Crawler Log Parser — Identifies AI bots from server access logs.

Supports AWS CloudFront, Cloudflare, and standard Apache/Nginx log formats.
Identifies GPTBot, ClaudeBot, Googlebot, PerplexityBot, etc.
"""

import re
from datetime import datetime, timezone

import structlog

from app.models.models import CrawlerLog, CrawlerType

logger = structlog.get_logger()

# AI crawler user-agent patterns
CRAWLER_PATTERNS = {
    CrawlerType.GPTBOT: re.compile(r"GPTBot", re.IGNORECASE),
    CrawlerType.CLAUDEBOT: re.compile(r"ClaudeBot|anthropic-ai", re.IGNORECASE),
    CrawlerType.PERPLEXITYBOT: re.compile(r"PerplexityBot", re.IGNORECASE),
    CrawlerType.GOOGLEBOT: re.compile(r"Googlebot|Google-Extended", re.IGNORECASE),
    CrawlerType.BINGBOT: re.compile(r"bingbot|msnbot", re.IGNORECASE),
    CrawlerType.METABOT: re.compile(r"meta-externalagent|facebookexternalhit", re.IGNORECASE),
    CrawlerType.BYTESPIDER: re.compile(r"Bytespider|ByteDance", re.IGNORECASE),
}

# Standard combined log format regex
# 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /path HTTP/1.1" 200 2326 "-" "UA"
COMBINED_LOG_RE = re.compile(
    r'(?P<ip>\S+)\s+\S+\s+\S+\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+\S+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\S+)\s+'
    r'"[^"]*"\s+"(?P<ua>[^"]*)"'
)

# CloudFront log format (tab-separated)
CLOUDFRONT_FIELDS = [
    "date", "time", "edge", "bytes", "ip", "method", "host", "path",
    "status", "referer", "ua", "query", "cookie", "edge_type", "request_id",
]


def identify_crawler(user_agent: str) -> CrawlerType:
    for crawler_type, pattern in CRAWLER_PATTERNS.items():
        if pattern.search(user_agent):
            return crawler_type
    return CrawlerType.UNKNOWN


def parse_combined_log_line(line: str) -> dict | None:
    match = COMBINED_LOG_RE.match(line.strip())
    if not match:
        return None

    ua = match.group("ua")
    crawler_type = identify_crawler(ua)
    if crawler_type == CrawlerType.UNKNOWN:
        return None  # Skip non-AI crawlers

    size = match.group("size")
    return {
        "ip_address": match.group("ip"),
        "user_agent": ua,
        "request_path": match.group("path"),
        "status_code": int(match.group("status")),
        "response_size_bytes": int(size) if size != "-" else 0,
        "crawler_type": crawler_type,
        "timestamp": _parse_log_timestamp(match.group("time")),
    }


def parse_cloudfront_log_line(line: str) -> dict | None:
    if line.startswith("#"):
        return None
    parts = line.strip().split("\t")
    if len(parts) < 15:
        return None

    fields = dict(zip(CLOUDFRONT_FIELDS, parts))
    ua = fields.get("ua", "")
    crawler_type = identify_crawler(ua)
    if crawler_type == CrawlerType.UNKNOWN:
        return None

    return {
        "ip_address": fields.get("ip", ""),
        "user_agent": ua,
        "request_path": fields.get("path", ""),
        "status_code": int(fields.get("status", 0)),
        "response_size_bytes": int(fields.get("bytes", 0)),
        "crawler_type": crawler_type,
        "timestamp": _parse_cloudfront_timestamp(
            fields.get("date", ""), fields.get("time", "")
        ),
    }


def parse_log_lines(lines: list[str], log_format: str = "combined") -> list[dict]:
    """Parse multiple log lines, returning only AI crawler entries."""
    parser = parse_combined_log_line if log_format == "combined" else parse_cloudfront_log_line
    results = []
    for line in lines:
        parsed = parser(line)
        if parsed:
            results.append(parsed)
    logger.info("logs_parsed", total_lines=len(lines), ai_crawlers_found=len(results))
    return results


def _parse_log_timestamp(time_str: str) -> datetime:
    try:
        return datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_cloudfront_timestamp(date_str: str, time_str: str) -> datetime:
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return datetime.now(timezone.utc)
