"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { listPrompts, getSentiment, type TrackedPrompt, type SentimentResponse } from "@/lib/api";

export default function PromptsPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [prompts, setPrompts] = useState<TrackedPrompt[]>([]);
    const [sentiment, setSentiment] = useState<SentimentResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            listPrompts(brand.id).catch(() => []),
            getSentiment(brand.id, 30).catch(() => null),
        ]).then(([p, s]) => {
            setPrompts(p);
            setSentiment(s);
            setLoading(false);
        });
    }, [brand]);

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Prompt Volumes</h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Discover what users ask AI engines about your industry and brand
            </p>

            {/* Tracked prompts */}
            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Tracked Prompts ({prompts.length})</h2>
                {prompts.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>
                        No prompts tracked yet. <a href="/dashboard/settings" style={{ color: "var(--primary)" }}>Add prompts →</a>
                    </p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Prompt</th><th style={th}>Language</th><th style={th}>Region</th><th style={th}>Active</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prompts.map((p) => (
                                <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={td}>{p.text}</td>
                                    <td style={td}>{p.language}</td>
                                    <td style={td}>{p.region}</td>
                                    <td style={td}>{p.is_active ? "✓" : "✕"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Top keywords from sentiment analysis */}
            {sentiment && sentiment.top_keywords.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Top Keywords (from AI responses)</h2>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {sentiment.top_keywords.map((k, i) => (
                            <span key={i} style={{
                                padding: "0.35rem 0.75rem",
                                borderRadius: 16,
                                fontSize: "0.8rem",
                                background: k.sentiment_bias === "positive" ? "#dcfce7" : k.sentiment_bias === "negative" ? "#fef2f2" : "var(--background)",
                                color: k.sentiment_bias === "positive" ? "#166534" : k.sentiment_bias === "negative" ? "#991b1b" : "var(--foreground)",
                                border: "1px solid var(--border)",
                            }}>
                                {k.word} ({k.count})
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Sentiment by engine */}
            {sentiment && sentiment.per_engine.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Sentiment by Engine</h2>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Engine</th><th style={th}>Positive</th><th style={th}>Neutral</th><th style={th}>Negative</th><th style={th}>Responses</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sentiment.per_engine.map((e, i) => (
                                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={{ ...td, fontWeight: 600 }}>{e.engine}</td>
                                    <td style={{ ...td, color: "#16a34a" }}>{e.positive_pct.toFixed(1)}%</td>
                                    <td style={td}>{e.neutral_pct.toFixed(1)}%</td>
                                    <td style={{ ...td, color: "#dc2626" }}>{e.negative_pct.toFixed(1)}%</td>
                                    <td style={td}>{e.total_responses}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
