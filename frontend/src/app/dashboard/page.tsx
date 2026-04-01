"use client";

import { useEffect, useState, useCallback } from "react";
import { useBrand } from "@/lib/hooks";
import { useCapture } from "@/lib/capture-context";
import {
    getCaptureStatus,
    getShareOfModel,
    getVisibility,
    getCrawlerStats,
    listPrompts,
    type CaptureStatus,
    type ShareOfModel,
    type VisibilityScore,
    type CrawlerStats,
} from "@/lib/api";

export default function DashboardPage() {
    const { brand, loading: brandLoading } = useBrand();
    const { capturing, captureResult, startCapture, clearResult, resumeIfRunning } = useCapture();
    const [som, setSom] = useState<ShareOfModel | null>(null);
    const [visibility, setVisibility] = useState<VisibilityScore[]>([]);
    const [crawlers, setCrawlers] = useState<CrawlerStats[]>([]);
    const [captureStatus, setCaptureStatus] = useState<CaptureStatus | null>(null);
    const [promptCount, setPromptCount] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async (brandId: string) => {
        setLoading(true);
        const [s, v, c, cs, p] = await Promise.all([
            getShareOfModel(brandId).catch(() => null),
            getVisibility(brandId, 7).catch(() => []),
            getCrawlerStats(brandId).catch(() => []),
            getCaptureStatus().catch(() => null),
            listPrompts(brandId).catch(() => []),
        ]);
        setSom(s);
        setVisibility(v);
        setCrawlers(c);
        setCaptureStatus(cs);
        setPromptCount(Array.isArray(p) ? p.length : 0);
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

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
                <StatCard label="Share of Model" value={som ? `${som.share_of_model.toFixed(1)}%` : "—"} sub={som ? `${som.brand_mentioned}/${som.total_responses} responses` : ""} />
                <StatCard label="Brand Mentions" value={loading ? "—" : String(totalMentions)} sub="Last 7 days" />
                <StatCard label="Avg Position" value={avgPosition != null ? avgPosition.toFixed(1) : "—"} sub="Across all engines" />
                <StatCard label="AI Crawler Visits" value={loading ? "—" : String(totalCrawlerVisits)} sub={`${crawlers.length} crawler types`} />
            </div>

            <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.5rem" }}>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Recent Visibility Scores</h2>
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
        <div style={{ background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)", padding: "1.25rem" }}>
            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", marginBottom: "0.5rem" }}>{label}</p>
            <p style={{ fontSize: "1.75rem", fontWeight: 700 }}>{value}</p>
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

const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--muted-foreground)" };
const td: React.CSSProperties = { padding: "0.5rem 0.75rem" };
