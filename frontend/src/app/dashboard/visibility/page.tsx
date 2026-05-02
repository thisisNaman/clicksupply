"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getVisibility, getPlatforms, getSentiment, type VisibilityScore, type PlatformStat, type SentimentResponse } from "@/lib/api";
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell,
} from "recharts";

const ENGINE_COLORS: Record<string, string> = {
    chatgpt: "#10b981", gemini: "#6366f1", perplexity: "#f59e0b",
    claude: "#ec4899", copilot: "#3b82f6",
};

export default function VisibilityPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [scores, setScores] = useState<VisibilityScore[]>([]);
    const [platforms, setPlatforms] = useState<PlatformStat[]>([]);
    const [sentiment, setSentiment] = useState<SentimentResponse | null>(null);
    const [days, setDays] = useState(30);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            getVisibility(brand.id, days).catch(() => []),
            getPlatforms(brand.id, days).catch(() => ({ platforms: [] })),
            getSentiment(brand.id, days).catch(() => null),
        ]).then(([v, p, s]) => {
            setScores(v);
            setPlatforms(p.platforms);
            setSentiment(s);
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
            <div className="stagger-children" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                {platforms.length > 0 ? platforms.map((p) => (
                    <div key={p.engine} className="card-hover" style={cardStyle}>
                        <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{p.engine}</p>
                        <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{p.visibility_score.toFixed(1)}%</p>
                        <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                            <span>Pos: {p.avg_position?.toFixed(1) ?? "—"}</span>
                            <span>Rate: {p.mention_rate.toFixed(0)}%</span>
                            <span>Cites: {p.citation_count}</span>
                        </div>
                    </div>
                )) : Object.entries(latestByEngine).map(([eng, s]) => (
                    <div key={eng} className="card-hover" style={cardStyle}>
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

            {/* Charts */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
                {/* SoM per Engine Line Chart */}
                <div style={cardStyle}>
                    <h2 style={sectionTitle}>Share of Model Over Time</h2>
                    {(() => {
                        // Pivot data: group by date, engines become series
                        const byDate: Record<string, Record<string, number>> = {};
                        const engines = new Set<string>();
                        for (const s of scores) {
                            const d = new Date(s.date).toLocaleDateString("en", { month: "short", day: "numeric" });
                            if (!byDate[d]) byDate[d] = {};
                            byDate[d][s.engine] = s.share_of_model;
                            engines.add(s.engine);
                        }
                        const chartData = Object.entries(byDate).map(([date, vals]) => ({ date, ...vals }));
                        if (chartData.length === 0) return <p style={{ color: "var(--muted-foreground)", fontSize: "0.85rem", height: 220, display: "flex", alignItems: "center", justifyContent: "center" }}>No data</p>;
                        return (
                            <ResponsiveContainer width="100%" height={220}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                                    <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" unit="%" />
                                    <Tooltip contentStyle={tooltipStyle} cursor={false} />
                                    <Legend wrapperStyle={{ fontSize: 12 }} />
                                    {[...engines].map((eng) => (
                                        <Line key={eng} type="monotone" dataKey={eng} stroke={ENGINE_COLORS[eng] ?? "#888"} strokeWidth={2} dot={false} name={eng} />
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        );
                    })()}
                </div>

                {/* Sentiment Donut */}
                <div style={cardStyle}>
                    <h2 style={sectionTitle}>Overall Sentiment</h2>
                    {(() => {
                        if (!sentiment || sentiment.per_engine.length === 0) return <p style={{ color: "var(--muted-foreground)", fontSize: "0.85rem", height: 220, display: "flex", alignItems: "center", justifyContent: "center" }}>No data</p>;
                        const totals = sentiment.per_engine.reduce(
                            (acc, e) => {
                                acc.positive += e.positive_pct * e.total_responses;
                                acc.neutral += e.neutral_pct * e.total_responses;
                                acc.negative += e.negative_pct * e.total_responses;
                                acc.total += e.total_responses;
                                return acc;
                            },
                            { positive: 0, neutral: 0, negative: 0, total: 0 },
                        );
                        const t = totals.total || 1;
                        const pieData = [
                            { name: "Positive", value: Math.round(totals.positive / t), color: "#34d399" },
                            { name: "Neutral", value: Math.round(totals.neutral / t), color: "#71717a" },
                            { name: "Negative", value: Math.round(totals.negative / t), color: "#f87171" },
                        ];
                        return (
                            <ResponsiveContainer width="100%" height={220}>
                                <PieChart>
                                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value" label={false}>
                                        {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                                    </Pie>
                                    <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} cursor={false} />
                                    <Legend
                                        layout="vertical" align="right" verticalAlign="middle"
                                        formatter={(value: string, entry: { payload?: { value?: number } }) => {
                                            const v = entry?.payload?.value ?? 0;
                                            return `${value} ${v}%`;
                                        }}
                                        wrapperStyle={{ fontSize: 12, lineHeight: "1.8em" }}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        );
                    })()}
                </div>
            </div>

            {/* Detailed table */}
            <div style={cardStyle}>
                <h2 style={sectionTitle}>All Scores ({scores.length})</h2>
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
                                        <td style={{ ...td, color: "var(--success)" }}>{s.positive_sentiment_pct.toFixed(0)}%</td>
                                        <td style={td}>{s.neutral_sentiment_pct.toFixed(0)}%</td>
                                        <td style={{ ...td, color: "var(--danger)" }}>{s.negative_sentiment_pct.toFixed(0)}%</td>
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

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.25rem" };
const sectionTitle: React.CSSProperties = { fontSize: "0.9rem", fontWeight: 600, marginBottom: "1rem", letterSpacing: "-0.01em" };
const tooltipStyle: React.CSSProperties = { background: "var(--tooltip-bg)", border: "1px solid var(--tooltip-border)", borderRadius: 8, fontSize: 12, color: "var(--foreground)" };
const selectStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.85rem" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
