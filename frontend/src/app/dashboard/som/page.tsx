"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getShareOfModel, getBenchmark, type ShareOfModel, type BenchmarkResponse } from "@/lib/api";

export default function ShareOfModelPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [som, setSom] = useState<ShareOfModel | null>(null);
    const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
    const [days, setDays] = useState(7);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            getShareOfModel(brand.id, days).catch(() => null),
            getBenchmark(brand.id, days).catch(() => null),
        ]).then(([s, b]) => {
            setSom(s);
            setBenchmark(b);
            setLoading(false);
        });
    }, [brand, days]);

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Share of Model</h1>
                <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={selectStyle}>
                    <option value={7}>7 days</option>
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                </select>
            </div>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Compare your brand&apos;s citation share against competitors across AI engines
            </p>

            {/* Main SoM card */}
            {som && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
                    <div style={cardStyle}>
                        <p style={cardLabel}>Share of Model</p>
                        <p style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--primary)" }}>{som.share_of_model.toFixed(1)}%</p>
                    </div>
                    <div style={cardStyle}>
                        <p style={cardLabel}>Brand Mentioned</p>
                        <p style={{ fontSize: "2.5rem", fontWeight: 700 }}>{som.brand_mentioned}</p>
                        <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>of {som.total_responses} responses</p>
                    </div>
                    <div style={cardStyle}>
                        <p style={cardLabel}>Period</p>
                        <p style={{ fontSize: "2.5rem", fontWeight: 700 }}>{som.period_days}d</p>
                    </div>
                </div>
            )}

            {/* Benchmark */}
            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Competitive Benchmark</h2>
                {!benchmark || (!benchmark.brand.avg_som && benchmark.competitors.length === 0) ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>No benchmark data yet. Run a capture and add competitors.</p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Brand</th><th style={th}>Avg SoM</th><th style={th}>Avg Position</th>
                                <th style={th}>Mentions</th><th style={th}>Positive %</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(var(--primary-rgb, 59, 130, 246), 0.05)" }}>
                                <td style={{ ...td, fontWeight: 600 }}>{benchmark.brand.name} ★</td>
                                <td style={td}>{benchmark.brand.avg_som.toFixed(1)}%</td>
                                <td style={td}>{benchmark.brand.avg_position?.toFixed(1) ?? "—"}</td>
                                <td style={td}>{benchmark.brand.mention_count}</td>
                                <td style={td}>{benchmark.brand.sentiment_positive_pct.toFixed(1)}%</td>
                            </tr>
                            {benchmark.competitors.map((c, i) => (
                                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={td}>{c.name}</td>
                                    <td style={td}>{c.avg_som.toFixed(1)}%</td>
                                    <td style={td}>{c.avg_position?.toFixed(1) ?? "—"}</td>
                                    <td style={td}>{c.mention_count}</td>
                                    <td style={td}>{c.sentiment_positive_pct.toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.25rem" };
const cardLabel: React.CSSProperties = { fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" };
const selectStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: 8, border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.85rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
