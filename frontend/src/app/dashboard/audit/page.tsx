"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

interface Recommendation {
    category: string;
    severity: string;
    title: string;
    description: string;
    action: string;
}

interface AuditResult {
    url: string;
    score: number;
    recommendations: Recommendation[];
    schema_suggestions: Record<string, unknown> | null;
    llms_txt_content: string | null;
}

const CATEGORY_LABELS: Record<string, string> = {
    content_structure: "Content Structure",
    schema_markup: "Schema Markup",
    technical: "Technical SEO",
    trust: "Trust & E-E-A-T",
};

const CATEGORY_ICONS: Record<string, string> = {
    content_structure: "📝",
    schema_markup: "🏷️",
    technical: "⚙️",
    trust: "🛡️",
};

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
    critical: { color: "var(--danger)", bg: "var(--danger-muted)", border: "rgba(248,113,113,0.25)", label: "Critical" },
    warning: { color: "var(--warning)", bg: "var(--warning-muted)", border: "rgba(251,191,36,0.25)", label: "Warning" },
    info: { color: "var(--primary)", bg: "var(--primary-muted)", border: "rgba(129,140,248,0.25)", label: "Info" },
};

function scoreColor(s: number) {
    if (s >= 80) return "var(--success)";
    if (s >= 60) return "var(--warning)";
    return "var(--danger)";
}

function scoreGrade(s: number) {
    if (s >= 90) return "A+";
    if (s >= 80) return "A";
    if (s >= 70) return "B";
    if (s >= 60) return "C";
    if (s >= 50) return "D";
    return "F";
}

export default function AuditPage() {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AuditResult | null>(null);
    const [activeTab, setActiveTab] = useState<string>("all");

    async function handleAudit() {
        if (!url) return;
        setLoading(true);
        setResult(null);
        try {
            const data = await api<AuditResult>("/aeo/audit", {
                method: "POST",
                body: { url },
            });
            setResult(data);
            setActiveTab("all");
        } catch {
            // handled by api() helper
        } finally {
            setLoading(false);
        }
    }

    const filteredRecs = result
        ? activeTab === "all"
            ? result.recommendations
            : result.recommendations.filter((r) => r.category === activeTab)
        : [];

    const categoryCounts = result
        ? result.recommendations.reduce(
            (acc, r) => {
                acc[r.category] = (acc[r.category] || 0) + 1;
                return acc;
            },
            {} as Record<string, number>,
        )
        : {};

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                AEO Audit
            </h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Audit any page for AI readiness — content structure, schema markup, trust signals
            </p>

            {/* URL input */}
            <div style={{ display: "flex", gap: "0.75rem", marginBottom: "2rem" }}>
                <input
                    type="url"
                    placeholder="https://example.com/page-to-audit"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAudit()}
                    style={{
                        flex: 1,
                        padding: "0.75rem 1rem",
                        borderRadius: 8,
                        border: "1px solid var(--border)",
                        background: "var(--card)",
                        color: "var(--foreground)",
                        fontSize: "0.95rem",
                    }}
                />
                <button
                    onClick={handleAudit}
                    disabled={loading || !url}
                    style={{
                        padding: "0.75rem 2rem",
                        borderRadius: 8,
                        background: "var(--gradient-primary)",
                        color: "white",
                        border: "none",
                        fontWeight: 600,
                        cursor: loading ? "wait" : "pointer",
                        opacity: loading || !url ? 0.6 : 1,
                    }}
                >
                    {loading ? "Auditing…" : "Run Audit"}
                </button>
            </div>

            {/* Loading skeleton */}
            <AnimatePresence>
                {loading && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
                    >
                        <div style={{ ...cardStyle, display: "flex", alignItems: "center", justifyContent: "center", padding: "3rem" }}>
                            <div style={{ textAlign: "center" }}>
                                <div className="animate-pulse-glow" style={{ width: 80, height: 80, borderRadius: "50%", background: "var(--primary-muted)", margin: "0 auto 1rem", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                    <span style={{ fontSize: "1.5rem" }}>🔍</span>
                                </div>
                                <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Analyzing page…</p>
                                <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)" }}>Checking content, schema, technical SEO & trust signals</p>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Results */}
            <AnimatePresence>
                {result && !loading && (
                    <motion.div
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        {/* Score hero */}
                        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
                            {/* Score circle */}
                            <motion.div
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: 0.1, duration: 0.4 }}
                                style={{ ...cardStyle, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem" }}
                            >
                                <p style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted-foreground)", fontWeight: 500, marginBottom: "0.75rem" }}>
                                    AEO Score
                                </p>
                                <div style={{ position: "relative", width: 110, height: 110 }}>
                                    <svg viewBox="0 0 110 110" style={{ width: 110, height: 110 }}>
                                        <circle cx="55" cy="55" r="48" fill="none" stroke="var(--border)" strokeWidth="7" />
                                        <motion.circle
                                            cx="55" cy="55" r="48" fill="none"
                                            stroke={scoreColor(result.score)}
                                            strokeWidth="7"
                                            strokeLinecap="round"
                                            strokeDasharray={`${result.score * 3.016} 301.6`}
                                            transform="rotate(-90 55 55)"
                                            initial={{ strokeDasharray: "0 301.6" }}
                                            animate={{ strokeDasharray: `${result.score * 3.016} 301.6` }}
                                            transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                                        />
                                    </svg>
                                    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                                        <motion.span
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: 0.5 }}
                                            style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em" }}
                                        >
                                            {result.score.toFixed(0)}
                                        </motion.span>
                                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: scoreColor(result.score) }}>
                                            {scoreGrade(result.score)}
                                        </span>
                                    </div>
                                </div>
                            </motion.div>

                            {/* Summary stats */}
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                                {Object.entries(categoryCounts).map(([cat, count], i) => {
                                    const sevCounts = result.recommendations
                                        .filter((r) => r.category === cat)
                                        .reduce((a, r) => { a[r.severity] = (a[r.severity] || 0) + 1; return a; }, {} as Record<string, number>);
                                    return (
                                        <motion.div
                                            key={cat}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.15 + i * 0.08 }}
                                            className="card-hover"
                                            onClick={() => setActiveTab(cat)}
                                            style={{
                                                ...cardStyle,
                                                cursor: "pointer",
                                                borderColor: activeTab === cat ? "var(--primary)" : "var(--border)",
                                            }}
                                        >
                                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                                                <span style={{ fontSize: "1.1rem" }}>{CATEGORY_ICONS[cat] || "📋"}</span>
                                                <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>{CATEGORY_LABELS[cat] || cat}</span>
                                            </div>
                                            <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.7rem" }}>
                                                {sevCounts.critical && (
                                                    <span style={{ color: "var(--danger)", fontWeight: 600 }}>
                                                        {sevCounts.critical} critical
                                                    </span>
                                                )}
                                                {sevCounts.warning && (
                                                    <span style={{ color: "var(--warning)", fontWeight: 600 }}>
                                                        {sevCounts.warning} warning
                                                    </span>
                                                )}
                                                {sevCounts.info && (
                                                    <span style={{ color: "var(--primary)" }}>
                                                        {sevCounts.info} info
                                                    </span>
                                                )}
                                            </div>
                                            <p style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: "0.25rem" }}>
                                                {count} <span style={{ fontSize: "0.7rem", fontWeight: 400, color: "var(--muted-foreground)" }}>issues</span>
                                            </p>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Filter tabs */}
                        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
                            {[{ key: "all", label: "All" }, ...Object.entries(CATEGORY_LABELS).map(([k, v]) => ({ key: k, label: v }))].map((tab) => (
                                <button
                                    key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    style={{
                                        padding: "0.4rem 0.85rem",
                                        borderRadius: 8,
                                        border: "1px solid",
                                        borderColor: activeTab === tab.key ? "var(--primary)" : "var(--border)",
                                        background: activeTab === tab.key ? "var(--primary-muted)" : "transparent",
                                        color: activeTab === tab.key ? "var(--primary)" : "var(--muted-foreground)",
                                        fontSize: "0.8rem",
                                        fontWeight: 500,
                                        cursor: "pointer",
                                    }}
                                >
                                    {tab.label}
                                    {tab.key !== "all" && categoryCounts[tab.key] && (
                                        <span style={{ marginLeft: "0.35rem", opacity: 0.7 }}>({categoryCounts[tab.key]})</span>
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* Recommendations list */}
                        <div className="stagger-children" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.5rem" }}>
                            {filteredRecs.map((rec, i) => {
                                const sev = SEVERITY_CONFIG[rec.severity] || SEVERITY_CONFIG.info;
                                return (
                                    <div
                                        key={i}
                                        style={{
                                            padding: "1rem 1.25rem",
                                            borderRadius: 12,
                                            background: sev.bg,
                                            border: `1px solid ${sev.border}`,
                                        }}
                                    >
                                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                                            <span
                                                style={{
                                                    padding: "0.15rem 0.5rem",
                                                    borderRadius: 6,
                                                    fontSize: "0.65rem",
                                                    fontWeight: 600,
                                                    textTransform: "uppercase",
                                                    letterSpacing: "0.05em",
                                                    color: sev.color,
                                                    background: "rgba(0,0,0,0.15)",
                                                }}
                                            >
                                                {sev.label}
                                            </span>
                                            <span style={{ fontSize: "0.7rem", color: "var(--muted-foreground)" }}>
                                                {CATEGORY_LABELS[rec.category] || rec.category}
                                            </span>
                                        </div>
                                        <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.35rem" }}>
                                            {rec.title}
                                        </h3>
                                        <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", lineHeight: 1.6, marginBottom: "0.5rem" }}>
                                            {rec.description}
                                        </p>
                                        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.78rem", color: sev.color, fontWeight: 500 }}>
                                            <span>→</span>
                                            <span>{rec.action}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Schema suggestions */}
                        {result.schema_suggestions && Object.keys(result.schema_suggestions).length > 0 && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.3 }}
                                style={{ ...cardStyle, marginBottom: "1.5rem" }}
                            >
                                <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                    <span>🏷️</span> Suggested Schema Markup
                                </h2>
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                    {Object.entries(result.schema_suggestions).map(([key, val]) => (
                                        <div key={key}>
                                            <p style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.35rem", textTransform: "capitalize" }}>
                                                {key.replace(/_/g, " ")}
                                            </p>
                                            <pre
                                                style={{
                                                    fontSize: "0.75rem",
                                                    padding: "0.75rem",
                                                    borderRadius: 8,
                                                    background: "var(--background)",
                                                    border: "1px solid var(--border)",
                                                    overflow: "auto",
                                                    maxHeight: 200,
                                                    whiteSpace: "pre-wrap",
                                                    color: "var(--muted-foreground)",
                                                }}
                                            >
                                                {typeof val === "string" ? val : JSON.stringify(val, null, 2)}
                                            </pre>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        {/* llms.txt */}
                        {result.llms_txt_content && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 }}
                                style={cardStyle}
                            >
                                <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                    <span>📄</span> Suggested llms.txt
                                </h2>
                                <pre
                                    style={{
                                        fontSize: "0.75rem",
                                        padding: "1rem",
                                        borderRadius: 8,
                                        background: "var(--background)",
                                        border: "1px solid var(--border)",
                                        overflow: "auto",
                                        maxHeight: 250,
                                        whiteSpace: "pre-wrap",
                                        color: "var(--muted-foreground)",
                                        lineHeight: 1.6,
                                    }}
                                >
                                    {result.llms_txt_content}
                                </pre>
                            </motion.div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Empty state */}
            {!result && !loading && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    style={{
                        ...cardStyle,
                        minHeight: 280,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        textAlign: "center",
                        padding: "3rem 2rem",
                    }}
                >
                    <span style={{ fontSize: "2.5rem", marginBottom: "1rem", opacity: 0.5 }}>🔍</span>
                    <p style={{ fontWeight: 600, marginBottom: "0.35rem" }}>Enter a URL to start</p>
                    <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", maxWidth: 380 }}>
                        We&apos;ll analyze the page for content structure, schema markup, technical SEO, and trust signals — and give you an actionable score.
                    </p>
                </motion.div>
            )}
        </div>
    );
}

const cardStyle: React.CSSProperties = {
    background: "var(--card)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--border)",
    padding: "1.25rem",
};
