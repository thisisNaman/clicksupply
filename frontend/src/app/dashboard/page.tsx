"use client";

import { useEffect, useState, useCallback } from "react";
import { useBrand } from "@/lib/hooks";
import { useCapture } from "@/lib/capture-context";
import {
    getCaptureStatus,
    getShareOfModel,
    getVisibility,
    getCrawlerStats,
    getSentiment,
    getTrends,
    listPrompts,
    getHealthScore,
    getSmartInsights,
    type CaptureStatus,
    type ShareOfModel,
    type VisibilityScore,
    type CrawlerStats,
    type SentimentResponse,
    type TrendsResponse,
    type HealthScoreResponse,
    type InsightsResponse,
    type InsightItem,
} from "@/lib/api";
import {
    AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

export default function DashboardPage() {
    const { brand, loading: brandLoading } = useBrand();
    const { capturing, captureResult, startCapture, clearResult, resumeIfRunning } = useCapture();
    const [som, setSom] = useState<ShareOfModel | null>(null);
    const [visibility, setVisibility] = useState<VisibilityScore[]>([]);
    const [crawlers, setCrawlers] = useState<CrawlerStats[]>([]);
    const [captureStatus, setCaptureStatus] = useState<CaptureStatus | null>(null);
    const [promptCount, setPromptCount] = useState<number | null>(null);
    const [trends, setTrends] = useState<TrendsResponse | null>(null);
    const [sentiment, setSentiment] = useState<SentimentResponse | null>(null);
    const [health, setHealth] = useState<HealthScoreResponse | null>(null);
    const [insights, setInsights] = useState<InsightsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async (brandId: string) => {
        setLoading(true);
        const [s, v, c, cs, p, t, sent, h, ins] = await Promise.all([
            getShareOfModel(brandId).catch(() => null),
            getVisibility(brandId, 7).catch(() => []),
            getCrawlerStats(brandId).catch(() => []),
            getCaptureStatus().catch(() => null),
            listPrompts(brandId).catch(() => []),
            getTrends(brandId, 30).catch(() => null),
            getSentiment(brandId, 30).catch(() => null),
            getHealthScore(brandId).catch(() => null),
            getSmartInsights(brandId).catch(() => null),
        ]);
        setSom(s);
        setVisibility(v);
        setCrawlers(c);
        setCaptureStatus(cs);
        setPromptCount(Array.isArray(p) ? p.length : 0);
        setTrends(t);
        setSentiment(sent);
        setHealth(h);
        setInsights(ins);
        setLoading(false);
    }, []);

    useEffect(() => {
        if (brand) loadData(brand.id);
    }, [brand, loadData]);

    // Resume polling if a capture is already running (e.g. page refresh)
    useEffect(() => {
        if (brand) resumeIfRunning(brand.id);
    }, [brand, resumeIfRunning]);

    // Refresh data when capture finishes
    useEffect(() => {
        if (captureResult && brand && !capturing) {
            loadData(brand.id);
        }
    }, [captureResult, capturing, brand, loadData]);

    async function handleCapture() {
        if (!brand || capturing) return;
        clearResult();
        await startCapture(brand.id);
    }

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;

    if (!brand) {
        return (
            <div style={{ padding: "2rem" }}>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Dashboard</h1>
                <p style={{ color: "var(--muted-foreground)", marginBottom: "1rem" }}>No brand set up yet.</p>
                <a href="/dashboard/setup" style={{ color: "var(--primary)", fontWeight: 600 }}>Set up your brand →</a>
            </div>
        );
    }

    const totalCrawlerVisits = crawlers.reduce((sum, c) => sum + c.total_visits, 0);
    const avgPosition = (() => {
        const positions = visibility.filter((v) => v.avg_generative_position != null);
        if (positions.length === 0) return null;
        return positions.reduce((s, v) => s + (v.avg_generative_position ?? 0), 0) / positions.length;
    })();
    const totalMentions = visibility.reduce((s, v) => s + v.mention_count, 0);

    const hasData = visibility.length > 0 || (som && som.total_responses > 0);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <div>
                    <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.25rem" }}>{brand.name} — Dashboard</h1>
                    <p style={{ color: "var(--muted-foreground)", marginBottom: "1.5rem" }}>{brand.domain ?? "No domain"} · {brand.industry ?? "No industry"}</p>
                </div>
                <button onClick={handleCapture} disabled={capturing || promptCount === 0} style={{ padding: "0.6rem 1.25rem", borderRadius: 8, border: "none", background: "var(--primary)", color: "#fff", fontWeight: 600, fontSize: "0.875rem", cursor: capturing ? "wait" : "pointer", opacity: (capturing || promptCount === 0) ? 0.7 : 1 }}>
                    {capturing ? "Capturing…" : "Run Capture"}
                </button>
            </div>

            {captureResult && !capturing && (
                <div style={{ padding: "0.75rem 1rem", borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)", marginBottom: "1.5rem", fontSize: "0.875rem" }}>{captureResult}</div>
            )}

            {/* Setup checklist when no data yet */}
            {!hasData && !loading && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                    <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "1rem" }}>Get Started</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.875rem" }}>
                        <SetupStep done={true} label="Brand created" detail={brand.name} />
                        <SetupStep done={(promptCount ?? 0) > 0} label="Tracked prompts" detail={promptCount ? `${promptCount} prompts auto-generated` : "Prompts will be generated during brand setup"} />
                        <SetupStep done={captureStatus?.analysis_mode === "copilot_sdk"} label="Analysis via Copilot SDK" detail={
                            captureStatus ? (
                                `${Object.keys(captureStatus.engines).length} engines available (browser capture + Copilot SDK analysis)`
                            ) : "Checking…"
                        } />
                        <SetupStep done={false} label="Run first capture" detail="Click 'Run Capture' above to query AI engines" />
                    </div>
                </div>
            )}

            {/* Skeleton loading state */}
            {loading && <DashboardSkeleton />}

            <div className="stagger-children" style={{ display: loading ? "none" : "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                <StatCard label="Share of Model" value={som ? `${som.share_of_model.toFixed(1)}%` : "—"} sub={som ? `${som.brand_mentioned}/${som.total_responses} responses` : ""} />
                <StatCard label="Brand Mentions" value={loading ? "—" : String(totalMentions)} sub="Last 7 days" />
                <StatCard label="Avg Position" value={avgPosition != null ? avgPosition.toFixed(1) : "—"} sub="Across all engines" />
                <StatCard label="AI Crawler Visits" value={loading ? "—" : String(totalCrawlerVisits)} sub={`${crawlers.length} crawler types`} />
            </div>

            {/* Health Score + Insights Row */}
            {hasData && !loading && (
                <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "1rem", marginBottom: "2rem" }}>
                    {/* Brand Health Score */}
                    <div style={{ ...cardStyle, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem 1.5rem" }}>
                        {health ? (
                            <>
                                <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500, marginBottom: "0.5rem" }}>Brand Health</p>
                                <div style={{ position: "relative", width: 120, height: 120, marginBottom: "0.75rem" }}>
                                    <svg viewBox="0 0 120 120" style={{ width: 120, height: 120 }}>
                                        <circle cx="60" cy="60" r="52" fill="none" stroke="var(--border)" strokeWidth="8" />
                                        <circle cx="60" cy="60" r="52" fill="none" stroke={health.score >= 70 ? "var(--success)" : health.score >= 40 ? "var(--warning)" : "var(--danger)"} strokeWidth="8"
                                            strokeDasharray={`${health.score * 3.27} 327`} strokeDashoffset="0"
                                            transform="rotate(-90 60 60)" strokeLinecap="round" />
                                    </svg>
                                    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                                        <span style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em" }}>{health.score.toFixed(0)}</span>
                                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: health.score >= 70 ? "var(--success)" : health.score >= 40 ? "var(--warning)" : "var(--danger)" }}>{health.grade}</span>
                                    </div>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.8rem", color: health.trend >= 0 ? "var(--success)" : "var(--danger)" }}>
                                    {health.trend >= 0 ? "↑" : "↓"} {Math.abs(health.trend).toFixed(1)}pts vs last period
                                </div>
                                {/* Pillar mini bars */}
                                <div style={{ width: "100%", marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                                    {Object.entries(health.pillars).map(([name, p]) => (
                                        <div key={name} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.7rem" }}>
                                            <span style={{ width: 90, color: "var(--muted-foreground)", textTransform: "capitalize" }}>{name.replace("_", " ")}</span>
                                            <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                                                <div style={{ width: `${p.score}%`, height: "100%", borderRadius: 3, background: p.score >= 70 ? "var(--success)" : p.score >= 40 ? "var(--warning)" : "var(--danger)", transition: "width 0.5s" }} />
                                            </div>
                                            <span style={{ width: 28, textAlign: "right", fontWeight: 600 }}>{p.score.toFixed(0)}</span>
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <p style={{ color: "var(--muted-foreground)", fontSize: "0.85rem" }}>Run a capture to see your health score</p>
                        )}
                    </div>

                    {/* Smart Insights Feed */}
                    <div style={cardStyle}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                            <h2 style={sectionTitle}>Intelligence Brief</h2>
                            {insights && <span style={{ fontSize: "0.7rem", color: "var(--muted-foreground)" }}>Updated {new Date(insights.generated_at).toLocaleString()}</span>}
                        </div>
                        {insights && insights.insights.length > 0 ? (
                            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: 340, overflowY: "auto" }}>
                                {insights.insights.map((ins, i) => (
                                    <InsightCard key={i} insight={ins} />
                                ))}
                            </div>
                        ) : (
                            <p style={{ color: "var(--muted-foreground)", fontSize: "0.85rem", padding: "2rem 0", textAlign: "center" }}>
                                Run a capture to generate insights about your brand
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Charts row */}
            <div className="stagger-children" style={{ display: loading ? "none" : "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
                {/* Visibility Trend Chart */}
                <div style={cardStyle}>
                    <h2 style={sectionTitle}>Visibility Trend (30d)</h2>
                    {trends && trends.series.length > 0 ? (
                        <ResponsiveContainer width="100%" height={240}>
                            <AreaChart data={trends.series.map(d => ({ ...d, date: new Date(d.date).toLocaleDateString("en", { month: "short", day: "numeric" }) }))}>
                                <defs>
                                    <linearGradient id="gradVis" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#818cf8" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#818cf8" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="gradMen" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                                <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                                <Tooltip contentStyle={tooltipStyle} cursor={false} />
                                <Area type="monotone" dataKey="visibility_score" stroke="#818cf8" fill="url(#gradVis)" strokeWidth={2} name="Visibility %" />
                                <Area type="monotone" dataKey="mention_count" stroke="#34d399" fill="url(#gradMen)" strokeWidth={2} name="Mentions" />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <p style={emptyChart}>No trend data yet</p>
                    )}
                </div>

                {/* Sentiment Breakdown Chart */}
                <div style={cardStyle}>
                    <h2 style={sectionTitle}>Sentiment by Engine</h2>
                    {sentiment && sentiment.per_engine.length > 0 ? (
                        <ResponsiveContainer width="100%" height={240}>
                            <BarChart data={sentiment.per_engine}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis dataKey="engine" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                                <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                                <Tooltip contentStyle={tooltipStyle} cursor={false} />
                                <Legend wrapperStyle={{ fontSize: 12 }} />
                                <Bar dataKey="positive_pct" name="Positive %" fill="#34d399" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="neutral_pct" name="Neutral %" fill="#71717a" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="negative_pct" name="Negative %" fill="#f87171" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p style={emptyChart}>No sentiment data yet</p>
                    )}
                </div>
            </div>

            <div style={{ ...cardStyle, display: loading ? "none" : "block" }}>
                <h2 style={sectionTitle}>Recent Visibility Scores</h2>
                {visibility.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>No visibility data yet. Click &quot;Run Capture&quot; to start tracking.</p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Date</th><th style={th}>Engine</th><th style={th}>SoM %</th><th style={th}>Mentions</th><th style={th}>Avg Pos</th><th style={th}>Positive %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {visibility.slice(0, 20).map((v, i) => (
                                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={td}>{new Date(v.date).toLocaleDateString()}</td>
                                    <td style={td}>{v.engine}</td>
                                    <td style={td}>{v.share_of_model.toFixed(1)}%</td>
                                    <td style={td}>{v.mention_count}</td>
                                    <td style={td}>{v.avg_generative_position?.toFixed(1) ?? "—"}</td>
                                    <td style={td}>{v.positive_sentiment_pct.toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub: string }) {
    return (
        <div className="card-hover" style={{ background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.25rem 1.5rem" }}>
            <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{label}</p>
            <p style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>{value}</p>
            {sub && <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", marginTop: "0.25rem" }}>{sub}</p>}
        </div>
    );
}

function SetupStep({ done, label, detail, href }: { done: boolean; label: string; detail: string; href?: string }) {
    const content = (
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <span style={{ width: 24, height: 24, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", background: done ? "var(--primary)" : "var(--muted)", color: done ? "#fff" : "var(--muted-foreground)" }}>
                {done ? "✓" : "○"}
            </span>
            <div>
                <p style={{ fontWeight: 600, color: done ? "var(--foreground)" : "var(--muted-foreground)" }}>{label}</p>
                <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>{detail}</p>
            </div>
        </div>
    );
    if (href && !done) {
        return <a href={href} style={{ textDecoration: "none", color: "inherit" }}>{content}</a>;
    }
    return content;
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.5rem" };
const sectionTitle: React.CSSProperties = { fontSize: "0.9rem", fontWeight: 600, marginBottom: "1rem", letterSpacing: "-0.01em" };
const tooltipStyle: React.CSSProperties = { background: "var(--tooltip-bg)", border: "1px solid var(--tooltip-border)", borderRadius: 8, fontSize: 12, color: "var(--foreground)" };
const emptyChart: React.CSSProperties = { color: "var(--muted-foreground)", fontSize: "0.85rem", height: 240, display: "flex", alignItems: "center", justifyContent: "center" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };

function DashboardSkeleton() {
    return (
        <>
            <style>{`
                @keyframes shimmer {
                    0% { background-position: -400px 0; }
                    100% { background-position: 400px 0; }
                }
                .skeleton {
                    background: linear-gradient(90deg, var(--border) 25%, rgba(255,255,255,0.06) 50%, var(--border) 75%);
                    background-size: 800px 100%;
                    animation: shimmer 1.5s infinite ease-in-out;
                    border-radius: var(--radius-sm);
                }
            `}</style>

            {/* Stat cards skeleton */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                {[0, 1, 2, 3].map(i => (
                    <div key={i} style={{ ...cardStyle, padding: "1.25rem 1.5rem" }}>
                        <div className="skeleton" style={{ height: 12, width: 100, marginBottom: 12 }} />
                        <div className="skeleton" style={{ height: 28, width: 80, marginBottom: 8 }} />
                        <div className="skeleton" style={{ height: 10, width: 120 }} />
                    </div>
                ))}
            </div>

            {/* Health + Insights skeleton */}
            <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "1rem", marginBottom: "2rem" }}>
                <div style={{ ...cardStyle, display: "flex", flexDirection: "column", alignItems: "center", padding: "2rem 1.5rem" }}>
                    <div className="skeleton" style={{ height: 12, width: 90, marginBottom: 16 }} />
                    <div className="skeleton" style={{ width: 120, height: 120, borderRadius: "50%", marginBottom: 12 }} />
                    <div className="skeleton" style={{ height: 10, width: 140, marginBottom: 16 }} />
                    {[0, 1, 2, 3, 4].map(i => (
                        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", marginBottom: 6 }}>
                            <div className="skeleton" style={{ height: 10, width: 80 }} />
                            <div className="skeleton" style={{ height: 6, flex: 1 }} />
                        </div>
                    ))}
                </div>
                <div style={cardStyle}>
                    <div className="skeleton" style={{ height: 14, width: 150, marginBottom: 16 }} />
                    {[0, 1, 2, 3].map(i => (
                        <div key={i} style={{ padding: "0.75rem 1rem", borderRadius: "var(--radius-sm)", background: "var(--border)", opacity: 0.3, marginBottom: 10 }}>
                            <div className="skeleton" style={{ height: 12, width: "60%", marginBottom: 8 }} />
                            <div className="skeleton" style={{ height: 10, width: "90%", marginBottom: 6 }} />
                            <div className="skeleton" style={{ height: 10, width: "40%" }} />
                        </div>
                    ))}
                </div>
            </div>

            {/* Charts skeleton */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
                {[0, 1].map(i => (
                    <div key={i} style={cardStyle}>
                        <div className="skeleton" style={{ height: 14, width: 180, marginBottom: 16 }} />
                        <div className="skeleton" style={{ height: 240, width: "100%" }} />
                    </div>
                ))}
            </div>

            {/* Table skeleton */}
            <div style={cardStyle}>
                <div className="skeleton" style={{ height: 14, width: 200, marginBottom: 16 }} />
                {[0, 1, 2, 3, 4].map(i => (
                    <div key={i} style={{ display: "flex", gap: "1rem", marginBottom: 12 }}>
                        {[80, 70, 50, 60, 50, 60].map((w, j) => (
                            <div key={j} className="skeleton" style={{ height: 12, width: w }} />
                        ))}
                    </div>
                ))}
            </div>
        </>
    );
}

const SEVERITY_STYLES: Record<string, { bg: string; border: string; icon: string; color: string }> = {
    critical: { bg: "var(--danger-muted)", border: "rgba(248,113,113,0.3)", icon: "🔴", color: "var(--danger)" },
    warning: { bg: "var(--warning-muted)", border: "rgba(251,191,36,0.3)", icon: "🟡", color: "var(--warning)" },
    opportunity: { bg: "var(--success-muted)", border: "rgba(52,211,153,0.3)", icon: "🟢", color: "var(--success)" },
    info: { bg: "var(--primary-muted)", border: "rgba(129,140,248,0.3)", icon: "💡", color: "var(--primary)" },
};

function InsightCard({ insight }: { insight: InsightItem }) {
    const style = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;
    return (
        <div style={{ padding: "0.75rem 1rem", borderRadius: "var(--radius-sm)", background: style.bg, border: `1px solid ${style.border}` }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.85rem", flexShrink: 0 }}>{style.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem", color: "var(--foreground)" }}>{insight.title}</p>
                    <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", lineHeight: 1.5 }}>{insight.description}</p>
                    {insight.action && (
                        <p style={{ fontSize: "0.7rem", color: style.color, marginTop: "0.35rem", fontWeight: 500 }}>→ {insight.action}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
