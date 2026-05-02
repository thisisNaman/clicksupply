"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import {
    listPrompts, addPrompt, updatePrompt, deletePrompt,
    getSentiment, getIntentDistribution, getTopicClusters,
    type TrackedPrompt, type SentimentResponse, type IntentResponse, type TopicClusterResponse,
} from "@/lib/api";
import {
    BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend,
} from "recharts";

export default function PromptsPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [prompts, setPrompts] = useState<TrackedPrompt[]>([]);
    const [sentiment, setSentiment] = useState<SentimentResponse | null>(null);
    const [intentData, setIntentData] = useState<IntentResponse | null>(null);
    const [topics, setTopics] = useState<TopicClusterResponse | null>(null);
    const [loading, setLoading] = useState(true);

    // Add prompt form
    const [newText, setNewText] = useState("");
    const [newLang, setNewLang] = useState("en");
    const [newRegion, setNewRegion] = useState("IN");

    // Edit state
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editText, setEditText] = useState("");
    const [editLang, setEditLang] = useState("");
    const [editRegion, setEditRegion] = useState("");

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        Promise.all([
            listPrompts(brand.id).catch(() => []),
            getSentiment(brand.id, 30).catch(() => null),
            getIntentDistribution(brand.id, 30).catch(() => null),
            getTopicClusters(brand.id, 30).catch(() => null),
        ]).then(([p, s, i, t]) => {
            setPrompts(p);
            setSentiment(s);
            setIntentData(i);
            setTopics(t);
            setLoading(false);
        });
    }, [brand]);

    async function handleAdd() {
        if (!newText.trim() || !brand) return;
        try {
            const p = await addPrompt(brand.id, { text: newText.trim(), language: newLang, region: newRegion });
            setPrompts((prev) => [...prev, p]);
            setNewText("");
        } catch { /* ignore */ }
    }

    async function handleSave(promptId: string) {
        if (!brand) return;
        try {
            const updated = await updatePrompt(brand.id, promptId, {
                text: editText, language: editLang, region: editRegion,
            });
            setPrompts((prev) => prev.map((p) => (p.id === promptId ? updated : p)));
            setEditingId(null);
        } catch { /* ignore */ }
    }

    async function handleDelete(promptId: string) {
        if (!brand) return;
        try {
            await deletePrompt(brand.id, promptId);
            setPrompts((prev) => prev.filter((p) => p.id !== promptId));
        } catch { /* ignore */ }
    }

    async function handleToggle(prompt: TrackedPrompt) {
        if (!brand) return;
        try {
            const updated = await updatePrompt(brand.id, prompt.id, { is_active: !prompt.is_active });
            setPrompts((prev) => prev.map((p) => (p.id === prompt.id ? updated : p)));
        } catch { /* ignore */ }
    }

    function startEdit(p: TrackedPrompt) {
        setEditingId(p.id);
        setEditText(p.text);
        setEditLang(p.language);
        setEditRegion(p.region);
    }

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    const intentColors: Record<string, string> = {
        informational: "#3b82f6", commercial: "#f59e0b", comparison: "#a78bfa",
        conversational: "#34d399", navigational: "#f87171",
    };

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Prompt Volumes</h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Manage tracked prompts, discover intent patterns, and see what users ask AI engines
            </p>

            {/* Add prompt */}
            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Add Prompt</h2>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <input type="text" value={newText} onChange={(e) => setNewText(e.target.value)}
                        placeholder="e.g. Best fintech apps in India" style={{ ...inputStyle, flex: 1, minWidth: 250 }}
                        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAdd())} />
                    <select value={newLang} onChange={(e) => setNewLang(e.target.value)} style={inputStyle}>
                        <option value="en">English</option><option value="hi">Hindi</option><option value="ta">Tamil</option>
                        <option value="te">Telugu</option><option value="bn">Bengali</option><option value="mr">Marathi</option>
                    </select>
                    <select value={newRegion} onChange={(e) => setNewRegion(e.target.value)} style={inputStyle}>
                        <option value="IN">India</option><option value="US">US</option><option value="UK">UK</option>
                        <option value="SG">Singapore</option><option value="AE">UAE</option>
                    </select>
                    <button onClick={handleAdd} style={btnPrimary}>Add</button>
                </div>
            </div>

            {/* Tracked prompts table */}
            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Tracked Prompts ({prompts.length})</h2>
                {prompts.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>No prompts tracked yet. Add one above.</p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Prompt</th><th style={th}>Language</th><th style={th}>Region</th>
                                <th style={th}>Intent</th><th style={th}>Active</th><th style={th}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prompts.map((p) => (
                                <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    {editingId === p.id ? (
                                        <>
                                            <td style={td}><input value={editText} onChange={(e) => setEditText(e.target.value)} style={{ ...inputStyle, width: "100%" }} /></td>
                                            <td style={td}><input value={editLang} onChange={(e) => setEditLang(e.target.value)} style={{ ...inputStyle, width: 60 }} /></td>
                                            <td style={td}><input value={editRegion} onChange={(e) => setEditRegion(e.target.value)} style={{ ...inputStyle, width: 60 }} /></td>
                                            <td style={td}><span style={intentBadge(p.intent)}>{p.intent || "—"}</span></td>
                                            <td style={td}>{p.is_active ? "✓" : "✕"}</td>
                                            <td style={td}>
                                                <button onClick={() => handleSave(p.id)} style={btnSmall}>Save</button>{" "}
                                                <button onClick={() => setEditingId(null)} style={btnSmallMuted}>Cancel</button>
                                            </td>
                                        </>
                                    ) : (
                                        <>
                                            <td style={td}>{p.text}</td>
                                            <td style={td}>{p.language}</td>
                                            <td style={td}>{p.region}</td>
                                            <td style={td}><span style={intentBadge(p.intent)}>{p.intent || "—"}</span></td>
                                            <td style={td}>
                                                <button onClick={() => handleToggle(p)} style={{ ...btnSmallMuted, cursor: "pointer" }}>
                                                    {p.is_active ? "✓" : "✕"}
                                                </button>
                                            </td>
                                            <td style={td}>
                                                <button onClick={() => startEdit(p)} style={btnSmall}>Edit</button>{" "}
                                                <button onClick={() => handleDelete(p.id)} style={btnSmallDanger}>Remove</button>
                                            </td>
                                        </>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Intent distribution + Chart */}
            {intentData && intentData.distribution.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Intent Distribution</h2>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                        {/* Pie Chart */}
                        <ResponsiveContainer width="100%" height={240}>
                            <PieChart>
                                <Pie
                                    data={intentData.distribution.map(d => ({
                                        name: d.intent, value: d.pct,
                                        fill: intentColors[d.intent] || "#666",
                                    }))}
                                    cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3}
                                    dataKey="value"
                                    label={({ name, value }) => `${name} ${value}%`}
                                >
                                    {intentData.distribution.map((d, i) => (
                                        <Cell key={i} fill={intentColors[d.intent] || "#666"} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={tooltipStyle} />
                            </PieChart>
                        </ResponsiveContainer>

                        {/* Stat cards */}
                        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignContent: "start" }}>
                            {intentData.distribution.map((d) => (
                                <div key={d.intent} style={{
                                    flex: "1 1 140px", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)",
                                    background: "var(--background)", textAlign: "center",
                                }}>
                                    <div style={{ fontSize: "1.5rem", fontWeight: 700, color: intentColors[d.intent] || "var(--foreground)" }}>{d.pct}%</div>
                                    <div style={{ fontSize: "0.8rem", textTransform: "capitalize", color: "var(--muted-foreground)" }}>{d.intent}</div>
                                    <div style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>{d.count} responses</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Top prompts per intent */}
                    <div style={{ marginTop: "1.5rem" }}>
                        {Object.entries(intentData.top_prompts_by_intent).map(([intent, prms]) => (
                            prms.length > 0 && (
                                <div key={intent} style={{ marginBottom: "1rem" }}>
                                    <h3 style={{ fontSize: "0.85rem", fontWeight: 600, textTransform: "capitalize", color: intentColors[intent] || "var(--foreground)", marginBottom: "0.5rem" }}>
                                        {intent}
                                    </h3>
                                    {prms.map((p, i) => (
                                        <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.25rem 0", fontSize: "0.8rem" }}>
                                            <span style={{ color: "var(--foreground)" }}>{p.text}</span>
                                            <span style={{ color: "var(--muted-foreground)", whiteSpace: "nowrap", marginLeft: "1rem" }}>{p.visibility_pct}% visibility</span>
                                        </div>
                                    ))}
                                </div>
                            )
                        ))}
                    </div>
                </div>
            )}

            {/* Topic Clustering */}
            {topics && topics.clusters.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Topic Clusters</h2>
                    <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "1rem" }}>
                        Prompts grouped by topic — {topics.total_topics} topics across {topics.total_prompts} prompts
                    </p>

                    {/* Topic visibility bar chart */}
                    <ResponsiveContainer width="100%" height={Math.max(200, topics.clusters.slice(0, 12).length * 36)}>
                        <BarChart data={topics.clusters.slice(0, 12)} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" unit="%" />
                            <YAxis type="category" dataKey="topic" width={140} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Bar dataKey="avg_visibility" name="Avg Visibility %" fill="#818cf8" radius={[0, 6, 6, 0]} />
                        </BarChart>
                    </ResponsiveContainer>

                    {/* Topic cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem", marginTop: "1.5rem" }}>
                        {topics.clusters.map((cluster) => (
                            <div key={cluster.topic} style={{
                                padding: "1rem", borderRadius: 8, border: "1px solid var(--border)", background: "var(--background)",
                            }}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                                    <span style={{ fontWeight: 600, fontSize: "0.85rem", textTransform: "capitalize" }}>{cluster.topic}</span>
                                    <span style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>{cluster.prompt_count} prompts</span>
                                </div>
                                <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>
                                    <span>Visibility: <strong style={{ color: "var(--foreground)" }}>{cluster.avg_visibility}%</strong></span>
                                    {cluster.avg_position && <span>Avg Pos: <strong style={{ color: "var(--foreground)" }}>{cluster.avg_position}</strong></span>}
                                    {cluster.dominant_intent && (
                                        <span style={intentBadge(cluster.dominant_intent)}>{cluster.dominant_intent}</span>
                                    )}
                                </div>
                                <div style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                                    {cluster.prompts.slice(0, 3).map((p, i) => (
                                        <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.15rem 0" }}>
                                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>{p.text}</span>
                                            <span>{p.visibility_pct}%</span>
                                        </div>
                                    ))}
                                    {cluster.prompts.length > 3 && <span style={{ color: "var(--primary)", fontSize: "0.7rem" }}>+{cluster.prompts.length - 3} more</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Top keywords */}
            {sentiment && sentiment.top_keywords.length > 0 && (
                <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem", marginBottom: "2rem" }}>
                    <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Top Keywords (from AI responses)</h2>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {sentiment.top_keywords.map((k, i) => (
                            <span key={i} style={{
                                padding: "0.35rem 0.75rem", borderRadius: 16, fontSize: "0.8rem",
                                background: k.sentiment_bias === "positive" ? "var(--success-muted)" : k.sentiment_bias === "negative" ? "var(--danger-muted)" : "var(--background)",
                                color: k.sentiment_bias === "positive" ? "var(--success)" : k.sentiment_bias === "negative" ? "var(--danger)" : "var(--foreground)",
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
                    <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={sentiment.per_engine}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis dataKey="engine" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                            <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" unit="%" />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={{ fontSize: 12 }} />
                            <Bar dataKey="positive_pct" name="Positive" fill="#34d399" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="neutral_pct" name="Neutral" fill="#71717a" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="negative_pct" name="Negative" fill="#f87171" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", marginTop: "1rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={th}>Engine</th><th style={th}>Positive</th><th style={th}>Neutral</th><th style={th}>Negative</th><th style={th}>Responses</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sentiment.per_engine.map((e, i) => (
                                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={{ ...td, fontWeight: 600 }}>{e.engine}</td>
                                    <td style={{ ...td, color: "var(--success)" }}>{e.positive_pct.toFixed(1)}%</td>
                                    <td style={td}>{e.neutral_pct.toFixed(1)}%</td>
                                    <td style={{ ...td, color: "var(--danger)" }}>{e.negative_pct.toFixed(1)}%</td>
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

const tooltipStyle: React.CSSProperties = { background: "var(--tooltip-bg)", border: "1px solid var(--tooltip-border)", borderRadius: 8, fontSize: 12, color: "var(--foreground)" };
const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
const inputStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--background)", color: "var(--foreground)", fontSize: "0.875rem" };
const btnPrimary: React.CSSProperties = { padding: "0.5rem 1rem", borderRadius: "var(--radius-sm)", border: "none", background: "var(--primary)", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.875rem" };
const btnSmall: React.CSSProperties = { padding: "0.25rem 0.5rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--primary)", background: "transparent", color: "var(--primary)", cursor: "pointer", fontSize: "0.75rem" };
const btnSmallMuted: React.CSSProperties = { padding: "0.25rem 0.5rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--border)", background: "transparent", color: "var(--muted-foreground)", cursor: "pointer", fontSize: "0.75rem" };
const btnSmallDanger: React.CSSProperties = { padding: "0.25rem 0.5rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--danger)", background: "transparent", color: "var(--danger)", cursor: "pointer", fontSize: "0.75rem" };

function intentBadge(intent: string | null): React.CSSProperties {
    const colors: Record<string, string> = {
        informational: "#3b82f6", commercial: "#f59e0b", comparison: "#a78bfa",
        conversational: "#34d399", navigational: "#f87171",
    };
    return {
        padding: "0.15rem 0.5rem", borderRadius: 10, fontSize: "0.7rem", fontWeight: 600,
        background: intent ? `${colors[intent] || "#666"}20` : "transparent",
        color: intent ? colors[intent] || "#666" : "var(--muted-foreground)",
    };
}
