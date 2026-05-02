"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getShareOfModel, getBenchmark, type ShareOfModel, type BenchmarkResponse } from "@/lib/api";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
    ResponsiveContainer, Legend, RadarChart, Radar, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

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

            {/* Benchmark Chart */}
            {benchmark && (benchmark.brand.avg_som > 0 || benchmark.competitors.length > 0) && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
                    {/* SoM Bar Chart */}
                    <div style={cardStyle}>
                        <h2 style={sectionTitle}>SoM Comparison</h2>
                        <ResponsiveContainer width="100%" height={240}>
                            <BarChart data={[
                                { name: benchmark.brand.name, som: benchmark.brand.avg_som, fill: "#818cf8" },
                                ...benchmark.competitors.map((c, i) => ({
                                    name: c.name, som: c.avg_som,
                                    fill: ["#f59e0b", "#34d399", "#ec4899", "#3b82f6", "#f87171"][i % 5],
                                })),
                            ]}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                                <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" unit="%" />
                                <Tooltip contentStyle={tooltipStyle} cursor={false} />
                                <Bar dataKey="som" name="SoM %" radius={[6, 6, 0, 0]}>
                                    {[benchmark.brand, ...benchmark.competitors].map((_, i) => {
                                        const colors = ["#818cf8", "#f59e0b", "#34d399", "#ec4899", "#3b82f6", "#f87171"];
                                        return <Cell key={i} fill={colors[i % colors.length]} />;
                                    })}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Radar Chart */}
                    <div style={cardStyle}>
                        <h2 style={sectionTitle}>Multi-Metric Comparison</h2>
                        {(() => {
                            const allBrands = [{ ...benchmark.brand, isTarget: true }, ...benchmark.competitors.map(c => ({ ...c, isTarget: false }))];
                            const maxSom = Math.max(...allBrands.map(b => b.avg_som), 1);
                            const maxMentions = Math.max(...allBrands.map(b => b.mention_count), 1);
                            const radarData = allBrands.map(b => ({
                                name: b.name,
                                SoM: Math.round(b.avg_som / maxSom * 100),
                                Mentions: Math.round(b.mention_count / maxMentions * 100),
                                Sentiment: Math.round(b.sentiment_positive_pct),
                            }));
                            return (
                                <ResponsiveContainer width="100%" height={240}>
                                    <RadarChart data={[
                                        { metric: "SoM", ...Object.fromEntries(radarData.map(d => [d.name, d.SoM])) },
                                        { metric: "Mentions", ...Object.fromEntries(radarData.map(d => [d.name, d.Mentions])) },
                                        { metric: "Sentiment", ...Object.fromEntries(radarData.map(d => [d.name, d.Sentiment])) },
                                    ]}>
                                        <PolarGrid stroke="var(--border)" />
                                        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                                        <PolarRadiusAxis tick={{ fontSize: 10 }} />
                                        {radarData.map((d, i) => {
                                            const colors = ["#6366f1", "#f59e0b", "#22c55e", "#ec4899"];
                                            return <Radar key={d.name} name={d.name} dataKey={d.name} stroke={colors[i % colors.length]} fill={colors[i % colors.length]} fillOpacity={0.15} />;
                                        })}
                                        <Legend wrapperStyle={{ fontSize: 12 }} />
                                        <Tooltip contentStyle={tooltipStyle} cursor={false} />
                                    </RadarChart>
                                </ResponsiveContainer>
                            );
                        })()}
                    </div>
                </div>
            )}

            {/* Benchmark */}
            <div style={cardStyle}>
                <h2 style={sectionTitle}>Competitive Benchmark</h2>
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
                            <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--primary-muted)" }}>
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

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.5rem" };
const cardLabel: React.CSSProperties = { fontSize: "0.75rem", color: "var(--muted-foreground)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 };
const sectionTitle: React.CSSProperties = { fontSize: "0.9rem", fontWeight: 600, marginBottom: "1rem", letterSpacing: "-0.01em" };
const tooltipStyle: React.CSSProperties = { background: "var(--tooltip-bg)", border: "1px solid var(--tooltip-border)", borderRadius: 8, fontSize: 12, color: "var(--foreground)" };
const selectStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.85rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
