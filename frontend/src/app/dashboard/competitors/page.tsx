"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import {
    listCompetitors, getBenchmark, getCoCitations, getPromptBrandMatrix,
    getCompetitiveCitations,
    type Competitor, type BenchmarkResponse, type CoCitationResponse,
    type PromptBrandMatrix, type CompetitorCitationsResponse,
} from "@/lib/api";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend, Cell,
} from "recharts";

export default function CompetitorsPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [competitors, setCompetitors] = useState<Competitor[]>([]);
    const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
    const [coCitations, setCoCitations] = useState<CoCitationResponse | null>(null);
    const [matrix, setMatrix] = useState<PromptBrandMatrix | null>(null);
    const [compCitations, setCompCitations] = useState<CompetitorCitationsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            listCompetitors(brand.id).catch(() => []),
            getBenchmark(brand.id, 30).catch(() => null),
            getCoCitations(brand.id, 30).catch(() => null),
            getPromptBrandMatrix(brand.id, 30).catch(() => null),
            getCompetitiveCitations(brand.id, 30).catch(() => null),
        ]).then(([c, b, cc, m, cit]) => {
            setCompetitors(c);
            setBenchmark(b);
            setCoCitations(cc);
            setMatrix(m);
            setCompCitations(cit);
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

                    {/* Benchmark Bar Chart */}
                    {benchmark && benchmark.competitors.length > 0 && (
                        <div style={{ ...cardStyle, marginTop: "2rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>SoM Comparison Chart</h2>
                            <ResponsiveContainer width="100%" height={260}>
                                <BarChart data={[
                                    { name: benchmark.brand.name, som: benchmark.brand.avg_som },
                                    ...benchmark.competitors.map((c) => ({ name: c.name, som: c.avg_som })),
                                ]} layout="vertical">
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                    <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" unit="%" />
                                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                                    <Tooltip contentStyle={tooltipStyle} />
                                    <Bar dataKey="som" name="SoM %" radius={[0, 6, 6, 0]}>
                                        {[benchmark.brand, ...benchmark.competitors].map((_, i) => {
                                            const colors = ["#818cf8", "#f59e0b", "#34d399", "#ec4899", "#3b82f6", "#f87171"];
                                            return <Cell key={i} fill={colors[i % colors.length]} />;
                                        })}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* Benchmark table */}
                    {benchmark && (
                        <div style={cardStyle}>
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
                            {benchmark.rankings.som_rank && (
                                <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--muted-foreground)" }}>
                                    Your brand ranks #{benchmark.rankings.som_rank} of {benchmark.rankings.total_entities} for Share of Model.
                                </p>
                            )}
                        </div>
                    )}

                    {/* Co-Citation Map */}
                    {(coCitations?.co_cited_brands?.length ?? 0) > 0 && (
                        <div style={{ ...cardStyle, marginTop: "2rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Co-Citation Map</h2>
                            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "1rem" }}>
                                Brands most frequently mentioned alongside yours in AI responses
                            </p>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                                <thead>
                                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                        <th style={th}>Brand</th><th style={th}>Co-appearances</th><th style={th}>Sentiment</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {coCitations!.co_cited_brands.map((b, i) => {
                                        const pct = coCitations!.total_responses_with_brand
                                            ? ((b.co_occurrence_count / coCitations!.total_responses_with_brand) * 100)
                                            : 0;
                                        return (
                                            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                                <td style={{ ...td, fontWeight: 600 }}>{b.name}</td>
                                                <td style={td}>
                                                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                                        <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                                                            <div style={{ width: `${pct}%`, height: "100%", background: "var(--primary)", borderRadius: 3 }} />
                                                        </div>
                                                        <span>{b.co_occurrence_count} ({pct.toFixed(1)}%)</span>
                                                    </div>
                                                </td>
                                                <td style={td}>{b.avg_sentiment}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Uncited Prompt Gaps */}
                    {(coCitations?.uncited_gaps?.length ?? 0) > 0 && (
                        <div style={{ ...cardStyle, marginTop: "2rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--danger)" }}>Uncited Prompt Gaps</h2>
                            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "1rem" }}>
                                Prompts where competitors appear but your brand is missing — highest-priority AEO opportunities
                            </p>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                                <thead>
                                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                        <th style={th}>Prompt</th><th style={th}>Competitors mentioned</th><th style={th}>Engines</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {coCitations!.uncited_gaps.map((g, i) => (
                                        <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                            <td style={td}>{g.prompt_text}</td>
                                            <td style={td}>
                                                <span style={{
                                                    padding: "0.1rem 0.4rem", borderRadius: 8, fontSize: "0.7rem",
                                                    background: "var(--danger-muted)", color: "var(--danger)", border: "1px solid rgba(248,113,113,0.3)",
                                                }}>{g.competitor_name}</span>
                                                <span style={{ marginLeft: "0.5rem", fontSize: "0.7rem", color: "var(--muted-foreground)" }}>
                                                    ({g.competitor_sentiment})
                                                </span>
                                            </td>
                                            <td style={td}>
                                                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                                                    {g.engines.map((e, j) => (
                                                        <span key={j} style={{
                                                            padding: "0.1rem 0.4rem", borderRadius: 8, fontSize: "0.7rem",
                                                            background: "var(--background)", border: "1px solid var(--border)",
                                                        }}>{e}</span>
                                                    ))}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Competitive Citations */}
                    {compCitations && (compCitations.your_top_domains.length > 0 || compCitations.competitors.length > 0) && (
                        <div style={{ ...cardStyle, marginTop: "2rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Competitive Citation Sources</h2>
                            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "1rem" }}>
                                Compare which domains/sources AI engines cite for your brand vs competitors
                            </p>

                            {/* Your top domains */}
                            {compCitations.your_top_domains.length > 0 && (
                                <div style={{ marginBottom: "1.5rem" }}>
                                    <h3 style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.75rem", color: "var(--primary)" }}>Your Top Citation Sources</h3>
                                    <ResponsiveContainer width="100%" height={Math.max(160, compCitations.your_top_domains.slice(0, 8).length * 32)}>
                                        <BarChart data={compCitations.your_top_domains.slice(0, 8)} layout="vertical">
                                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                            <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                                            <YAxis type="category" dataKey="domain" width={160} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                                            <Tooltip contentStyle={tooltipStyle} />
                                            <Bar dataKey="count" name="Citations" fill="#818cf8" radius={[0, 6, 6, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )}

                            {/* Competitor domains */}
                            {compCitations.competitors.map((comp) => comp.top_domains.length > 0 && (
                                <div key={comp.competitor_name} style={{ marginBottom: "1.5rem" }}>
                                    <h3 style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.75rem", color: "#f59e0b" }}>{comp.competitor_name} — Top Sources ({comp.total_citations} citations)</h3>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                        {comp.top_domains.slice(0, 10).map((d, i) => (
                                            <span key={i} style={{
                                                padding: "0.2rem 0.6rem", borderRadius: 8, fontSize: "0.75rem",
                                                background: compCitations.overlap_domains.includes(d.domain) ? "var(--primary-muted)" : "var(--muted)",
                                                border: `1px solid ${compCitations.overlap_domains.includes(d.domain) ? "var(--primary)" : "var(--border)"}`,
                                            }}>
                                                {d.domain} ({d.count})
                                                {compCitations.overlap_domains.includes(d.domain) && " 🔗"}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}

                            {compCitations.overlap_domains.length > 0 && (
                                <div style={{ padding: "0.75rem 1rem", borderRadius: 8, background: "var(--primary-muted)", border: "1px solid rgba(129,140,248,0.3)", fontSize: "0.8rem" }}>
                                    <strong>Shared domains ({compCitations.overlap_domains.length}):</strong>{" "}
                                    {compCitations.overlap_domains.join(", ")}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Prompt-wise Brand Distribution Matrix */}
                    {(matrix?.prompts?.length ?? 0) > 0 && (
                        <div style={{ ...cardStyle, marginTop: "2rem" }}>
                            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Prompt-wise Brand Distribution</h2>
                            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "1rem" }}>
                                Which brands appear for each prompt across AI engines ({matrix!.total_prompts} prompts, {matrix!.brands_found.length} brands)
                            </p>
                            <div style={{ overflowX: "auto" }}>
                                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", minWidth: 600 }}>
                                    <thead>
                                        <tr style={{ borderBottom: "2px solid var(--border)" }}>
                                            <th style={{ ...th, position: "sticky", left: 0, background: "var(--card)", zIndex: 1, minWidth: 200 }}>Prompt</th>
                                            <th style={{ ...th, minWidth: 70 }}>Intent</th>
                                            {matrix!.brands_found.map((b) => (
                                                <th key={b} style={{ ...th, textAlign: "center", minWidth: 100, whiteSpace: "nowrap" }}>
                                                    {b === brand?.name ? <strong>{b} ★</strong> : b}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {matrix!.prompts.map((p) => {
                                            const targetMissing = !p.brand_mentions.some((b) => b.is_target && b.mention_count > 0);
                                            return (
                                                <tr key={p.prompt_id} style={{ borderBottom: "1px solid var(--border)", background: targetMissing ? "rgba(239,68,68,0.04)" : undefined }}>
                                                    <td style={{ ...td, position: "sticky", left: 0, background: targetMissing ? "rgba(239,68,68,0.04)" : "var(--card)", zIndex: 1, maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                                                        title={p.prompt_text}>
                                                        {p.prompt_text}
                                                    </td>
                                                    <td style={td}>
                                                        {p.intent ? <span style={intentBadgeStyle(p.intent)}>{p.intent}</span> : "—"}
                                                    </td>
                                                    {matrix!.brands_found.map((bName) => {
                                                        const mention = p.brand_mentions.find((m) => m.name === bName);
                                                        if (!mention || mention.mention_count === 0) {
                                                            return <td key={bName} style={{ ...td, textAlign: "center", color: "var(--muted-foreground)" }}>—</td>;
                                                        }
                                                        const sentColor = mention.dominant_sentiment === "positive" ? "var(--success)"
                                                            : mention.dominant_sentiment === "negative" ? "var(--danger)" : "var(--muted-foreground)";
                                                        return (
                                                            <td key={bName} style={{ ...td, textAlign: "center" }}>
                                                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                                                                    <div style={{ display: "flex", flexWrap: "wrap", gap: 2, justifyContent: "center" }}>
                                                                        {mention.engines.map((e) => (
                                                                            <span key={e} style={{
                                                                                padding: "1px 4px", borderRadius: 4, fontSize: "0.6rem",
                                                                                background: mention.is_target ? "rgba(59,130,246,0.1)" : "var(--background)",
                                                                                border: `1px solid ${mention.is_target ? "#3b82f6" : "var(--border)"}`,
                                                                                color: mention.is_target ? "#3b82f6" : "var(--foreground)",
                                                                            }}>{e}</span>
                                                                        ))}
                                                                    </div>
                                                                    <span style={{ fontSize: "0.65rem", color: sentColor }}>
                                                                        {mention.avg_position ? `#${mention.avg_position}` : ""} {mention.dominant_sentiment}
                                                                    </span>
                                                                </div>
                                                            </td>
                                                        );
                                                    })}
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.5rem" };
const tooltipStyle: React.CSSProperties = { background: "var(--tooltip-bg)", border: "1px solid var(--tooltip-border)", borderRadius: 8, fontSize: 12, color: "var(--foreground)" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };

const intentColors: Record<string, string> = {
    informational: "#3b82f6", commercial: "#f59e0b", comparison: "#a78bfa",
    conversational: "#34d399", navigational: "#f87171",
};
function intentBadgeStyle(intent: string): React.CSSProperties {
    const c = intentColors[intent] || "#666";
    return { padding: "0.1rem 0.4rem", borderRadius: 8, fontSize: "0.65rem", fontWeight: 600, background: `${c}20`, color: c };
}
