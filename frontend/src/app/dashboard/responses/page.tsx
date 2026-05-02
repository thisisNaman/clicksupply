"use client";

import { useEffect, useState } from "react";
import { useBrand } from "@/lib/hooks";
import { getResponsesDetail, type AIResponseDetail } from "@/lib/api";

const ENGINES = ["chatgpt", "gemini", "perplexity", "claude", "copilot"];
const LANGUAGES = ["en", "hi", "de", "fr", "es", "ja"];
const REGIONS = ["IN", "US", "GB", "DE", "FR", "JP"];

export default function ResponsesPage() {
    const { brand, loading: brandLoading } = useBrand();
    const [responses, setResponses] = useState<AIResponseDetail[]>([]);
    const [loading, setLoading] = useState(true);
    const [engine, setEngine] = useState("");
    const [language, setLanguage] = useState("");
    const [region, setRegion] = useState("");
    const [expanded, setExpanded] = useState<Set<string>>(new Set());

    useEffect(() => {
        if (!brand) return;
        setLoading(true);
        getResponsesDetail(brand.id, {
            engine: engine || undefined,
            language: language || undefined,
            region: region || undefined,
            limit: 100,
        })
            .then(setResponses)
            .catch(() => setResponses([]))
            .finally(() => setLoading(false));
    }, [brand, engine, language, region]);

    const toggle = (id: string) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    const sentimentColor = (s: string | null) =>
        s === "positive" ? "var(--success)" : s === "negative" ? "var(--danger)" : "var(--muted-foreground)";

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Response Viewer</h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "1.5rem" }}>
                Inspect raw AI responses to understand how your brand is described
            </p>

            {/* Filters */}
            <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
                <select value={engine} onChange={(e) => setEngine(e.target.value)} style={selectStyle}>
                    <option value="">All Engines</option>
                    {ENGINES.map((e) => <option key={e} value={e}>{e}</option>)}
                </select>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} style={selectStyle}>
                    <option value="">All Languages</option>
                    {LANGUAGES.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
                </select>
                <select value={region} onChange={(e) => setRegion(e.target.value)} style={selectStyle}>
                    <option value="">All Regions</option>
                    {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <span style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", alignSelf: "center" }}>
                    {responses.length} responses
                </span>
            </div>

            {loading ? (
                <div style={{ color: "var(--muted-foreground)", padding: "2rem" }}>Loading responses…</div>
            ) : responses.length === 0 ? (
                <div style={{ ...cardStyle, textAlign: "center", color: "var(--muted-foreground)", padding: "3rem" }}>
                    No responses found. Run a capture first.
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {responses.map((r) => {
                        const isOpen = expanded.has(r.id);
                        const brands = (r.extra_metadata?.brands_mentioned ?? []) as { name: string; sentiment: string }[];
                        return (
                            <div key={r.id} style={cardStyle}>
                                {/* Header */}
                                <div
                                    style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", cursor: "pointer" }}
                                    onClick={() => toggle(r.id)}
                                >
                                    <div style={{ flex: 1 }}>
                                        <p style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                                            {r.prompt_text}
                                        </p>
                                        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
                                            <span style={badgeStyle}>{r.engine}</span>
                                            <span style={{ color: sentimentColor(r.sentiment) }}>
                                                {r.sentiment ?? "—"}
                                            </span>
                                            <span>Pos: {r.generative_position ?? "—"}</span>
                                            <span>{r.brand_mentioned ? "✓ Mentioned" : "✗ Not mentioned"}</span>
                                            {r.prompt_language && <span>Lang: {r.prompt_language.toUpperCase()}</span>}
                                            {r.prompt_region && <span>Region: {r.prompt_region}</span>}
                                            <span>{new Date(r.captured_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <span style={{ fontSize: "1rem", color: "var(--muted-foreground)", marginLeft: "1rem" }}>
                                        {isOpen ? "▾" : "▸"}
                                    </span>
                                </div>

                                {/* Expanded content */}
                                {isOpen && (
                                    <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
                                        {/* Brands mentioned */}
                                        {brands.length > 0 && (
                                            <div style={{ marginBottom: "1rem" }}>
                                                <p style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--muted-foreground)" }}>
                                                    BRANDS MENTIONED
                                                </p>
                                                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                                    {brands.map((b, i) => (
                                                        <span key={i} style={{
                                                            ...badgeStyle,
                                                            background: b.sentiment === "positive" ? "var(--success-muted)" : b.sentiment === "negative" ? "var(--danger-muted)" : "var(--muted)",
                                                            color: sentimentColor(b.sentiment),
                                                            border: "1px solid " + sentimentColor(b.sentiment) + "33",
                                                        }}>
                                                            {b.name} ({b.sentiment})
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Citations */}
                                        {r.citations && (
                                            <div style={{ marginBottom: "1rem" }}>
                                                <p style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--muted-foreground)" }}>
                                                    CITATIONS
                                                </p>
                                                <div style={{ fontSize: "0.8rem" }}>
                                                    {(Array.isArray(r.citations) ? r.citations : (r.citations as Record<string, unknown>).urls as unknown[] ?? []).map((c: unknown, i: number) => {
                                                        const cite = c as { domain?: string; url?: string; title?: string };
                                                        return (
                                                            <div key={i} style={{ marginBottom: "0.25rem" }}>
                                                                <span style={{ color: "var(--primary)" }}>{cite.domain || cite.url || "—"}</span>
                                                                {cite.title && <span style={{ marginLeft: "0.5rem", color: "var(--muted-foreground)" }}>{cite.title}</span>}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        {/* Raw response */}
                                        <div>
                                            <p style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--muted-foreground)" }}>
                                                RAW RESPONSE
                                            </p>
                                            <div style={{
                                                background: "var(--background)",
                                                borderRadius: 8,
                                                padding: "1rem",
                                                fontSize: "0.8rem",
                                                lineHeight: 1.6,
                                                whiteSpace: "pre-wrap",
                                                maxHeight: 400,
                                                overflowY: "auto",
                                                border: "1px solid var(--border)",
                                            }}>
                                                {r.raw_response || "No raw response stored."}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
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
const selectStyle: React.CSSProperties = {
    padding: "0.5rem 0.75rem",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    background: "var(--background)",
    color: "var(--foreground)",
    fontSize: "0.85rem",
};
const badgeStyle: React.CSSProperties = {
    padding: "0.15rem 0.5rem",
    borderRadius: "var(--radius-xs)",
    background: "var(--muted)",
    fontSize: "0.75rem",
};
