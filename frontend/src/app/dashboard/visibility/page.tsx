"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getVisibility, getPlatforms, type VisibilityScore, type PlatformStat } from "@/lib/api";

export default function VisibilityPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [scores, setScores] = useState<VisibilityScore[]>([]);
    const [platforms, setPlatforms] = useState<PlatformStat[]>([]);
    const [days, setDays] = useState(30);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            getVisibility(brand.id, days).catch(() => []),
            getPlatforms(brand.id, days).catch(() => ({ platforms: [] })),
        ]).then(([v, p]) => {
            setScores(v);
            setPlatforms(p.platforms);
            setLoading(false);
        });
    }, [brand, days]);

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    // Group latest score per engine
    const latestByEngine: Record<string, VisibilityScore> = {};
    for (const s of scores) {
        if (!latestByEngine[s.engine] || s.date > latestByEngine[s.engine].date) {
            latestByEngine[s.engine] = s;
        }
    }

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Visibility Scores</h1>
                <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={selectStyle}>
                    <option value={7}>7 days</option>
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                </select>
            </div>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Track your brand&apos;s visibility across AI answer engines over time
            </p>

            {/* Platform cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                {platforms.length > 0 ? platforms.map((p) => (
                    <div key={p.engine} style={cardStyle}>
                        <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{p.engine}</p>
                        <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{p.visibility_score.toFixed(1)}%</p>
                        <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                            <span>Pos: {p.avg_position?.toFixed(1) ?? "—"}</span>
                            <span>Rate: {p.mention_rate.toFixed(0)}%</span>
                            <span>Cites: {p.citation_count}</span>
                        </div>
                    </div>
                )) : Object.entries(latestByEngine).map(([eng, s]) => (
                    <div key={eng} style={cardStyle}>
                        <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{eng}</p>
                        <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{s.share_of_model.toFixed(1)}%</p>
                        <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                            <span>Mentions: {s.mention_count}</span>
                            <span>Pos: {s.avg_generative_position?.toFixed(1) ?? "—"}</span>
                        </div>
                    </div>
                ))}
                {platforms.length === 0 && Object.keys(latestByEngine).length === 0 && !loading && (
                    <div style={{ ...cardStyle, gridColumn: "1 / -1", textAlign: "center", color: "var(--muted-foreground)" }}>
                        No visibility data yet. Run a capture from the dashboard.
                    </div>
                )}
            </div>

            {/* Detailed table */}
            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>All Scores ({scores.length})</h2>
                {scores.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>No data for this period.</p>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                            <thead>
                                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                    <th style={th}>Date</th><th style={th}>Engine</th><th style={th}>SoM %</th>
                                    <th style={th}>Mentions</th><th style={th}>Total</th><th style={th}>Avg Pos</th>
                                    <th style={th}>+</th><th style={th}>~</th><th style={th}>−</th>
                                </tr>
                            </thead>
                            <tbody>
                                {scores.map((s, i) => (
                                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                        <td style={td}>{new Date(s.date).toLocaleDateString()}</td>
                                        <td style={td}>{s.engine}</td>
                                        <td style={td}>{s.share_of_model.toFixed(1)}%</td>
                                        <td style={td}>{s.mention_count}</td>
                                        <td style={td}>{s.total_prompts_run}</td>
                                        <td style={td}>{s.avg_generative_position?.toFixed(1) ?? "—"}</td>
                                        <td style={{ ...td, color: "#16a34a" }}>{s.positive_sentiment_pct.toFixed(0)}%</td>
                                        <td style={td}>{s.neutral_sentiment_pct.toFixed(0)}%</td>
                                        <td style={{ ...td, color: "#dc2626" }}>{s.negative_sentiment_pct.toFixed(0)}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.25rem" };
const selectStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: 8, border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.85rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
