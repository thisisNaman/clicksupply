"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getCrawlerStats, type CrawlerStats } from "@/lib/api";

export default function CrawlersPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [crawlers, setCrawlers] = useState<CrawlerStats[]>([]);
    const [days, setDays] = useState(30);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        getCrawlerStats(brand.id, days)
            .then(setCrawlers)
            .catch(() => setCrawlers([]))
            .finally(() => setLoading(false));
    }, [brand, days]);

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    const totalVisits = crawlers.reduce((s, c) => s + c.total_visits, 0);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Agent Analytics</h1>
                <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={selectStyle}>
                    <option value={7}>7 days</option>
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                </select>
            </div>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Monitor GPTBot, ClaudeBot, and other AI crawlers accessing your content
            </p>

            {/* Crawler cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                {crawlers.length > 0 ? crawlers.map((c) => (
                    <div key={c.crawler_type} style={cardStyle}>
                        <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{c.crawler_type}</p>
                        <p style={{ fontSize: "1.75rem", fontWeight: 700 }}>{c.total_visits}</p>
                        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                            <span>{c.unique_paths} paths</span>
                            <span>{(c.avg_response_size / 1024).toFixed(1)} KB avg</span>
                        </div>
                    </div>
                )) : !loading && (
                    <div style={{ ...cardStyle, gridColumn: "1 / -1", textAlign: "center", color: "var(--muted-foreground)" }}>
                        No crawler data yet. Upload your server access logs via the Agent Analytics API.
                    </div>
                )}
            </div>

            {/* Summary */}
            {crawlers.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Crawler Details</h2>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Crawler</th><th style={th}>Visits</th><th style={th}>Unique Paths</th>
                                <th style={th}>Avg Size</th><th style={th}>Last Seen</th>
                            </tr>
                        </thead>
                        <tbody>
                            {crawlers.map((c) => (
                                <tr key={c.crawler_type} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={{ ...td, fontWeight: 600 }}>{c.crawler_type}</td>
                                    <td style={td}>{c.total_visits}</td>
                                    <td style={td}>{c.unique_paths}</td>
                                    <td style={td}>{(c.avg_response_size / 1024).toFixed(1)} KB</td>
                                    <td style={td}>{c.latest_visit ? new Date(c.latest_visit).toLocaleDateString() : "—"}</td>
                                </tr>
                            ))}
                            <tr style={{ fontWeight: 600 }}>
                                <td style={td}>Total</td>
                                <td style={td}>{totalVisits}</td>
                                <td style={td} colSpan={3}></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.25rem" };
const selectStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: 8, border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.85rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
