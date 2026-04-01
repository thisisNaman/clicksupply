"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { listCompetitors, getBenchmark, type Competitor, type BenchmarkResponse } from "@/lib/api";

export default function CompetitorsPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [competitors, setCompetitors] = useState<Competitor[]>([]);
    const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            listCompetitors(brand.id).catch(() => []),
            getBenchmark(brand.id, 30).catch(() => null),
        ]).then(([c, b]) => {
            setCompetitors(c);
            setBenchmark(b);
            setLoading(false);
        });
    }, [brand]);

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Competitors</h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Track and benchmark competitor brands across AI answer engines
            </p>

            {competitors.length === 0 && !loading ? (
                <div style={{ ...cardStyle, textAlign: "center", color: "var(--muted-foreground)", padding: "3rem" }}>
                    No competitors added yet. <a href="/dashboard/settings" style={{ color: "var(--primary)" }}>Add competitors →</a>
                </div>
            ) : (
                <>
                    {/* Competitor cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                        {competitors.map((c) => {
                            const benchComp = benchmark?.competitors.find((bc) => bc.name === c.name);
                            return (
                                <div key={c.id} style={cardStyle}>
                                    <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{c.name}</p>
                                    <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{c.domain ?? "No domain"}</p>
                                    {benchComp && (
                                        <div style={{ fontSize: "0.8rem", color: "var(--muted-foreground)" }}>
                                            <span>SoM: {benchComp.avg_som.toFixed(1)}%</span>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Benchmark table */}
                    {benchmark && (
                        <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
                                Competitive Benchmark (30 days)
                            </h2>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                                <thead>
                                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                        <th style={th}>Brand</th><th style={th}>Avg SoM</th><th style={th}>Avg Position</th>
                                        <th style={th}>Mentions</th><th style={th}>Positive %</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(59, 130, 246, 0.05)" }}>
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
                            {benchmark.rankings.som_rank && (
                                <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--muted-foreground)" }}>
                                    Your brand ranks #{benchmark.rankings.som_rank} of {benchmark.rankings.total_entities} for Share of Model.
                                </p>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.25rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
