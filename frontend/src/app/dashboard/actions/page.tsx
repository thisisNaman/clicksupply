"use client";

import { useEffect, useState, useRef } from "react";
import { useBrand } from "@/lib/hooks";
import { useActions } from "@/lib/action-context";
import {
    updateActionStatus, verifyAction,
    type ActionsResponse, type ActionItem,
} from "@/lib/api";

const IMPACT_COLORS: Record<string, string> = { high: "var(--danger)", medium: "var(--warning)", low: "var(--success)" };
const EFFORT_COLORS: Record<string, string> = { low: "var(--success)", medium: "var(--warning)", high: "var(--danger)" };
const CATEGORY_ICONS: Record<string, string> = {
    content_gap: "📝", content_rewrite: "✍️", schema_markup: "🏷️", engine_optimization: "⚙️",
    website_audit: "🔍", crawler_analysis: "🕷️", best_practice: "✨",
};
const STATUS_LABELS: Record<string, string> = {
    pending: "To Do", in_progress: "In Progress", completed: "Done", dismissed: "Dismissed",
};
const VERIFY_LABELS: Record<string, { label: string; color: string }> = {
    improved: { label: "Improved", color: "var(--success)" },
    no_change: { label: "No Change", color: "var(--warning)" },
    regressed: { label: "Regressed", color: "var(--danger)" },
    error: { label: "Check Failed", color: "var(--muted-foreground)" },
};

const PROGRESS_ICONS: Record<number, string> = { 1: "🔍", 2: "🕷️", 3: "📊", 4: "✍️", 5: "⚙️", 6: "✨" };

const ENGINE_NAMES: Record<string, string> = {
    chatgpt: "ChatGPT", perplexity: "Perplexity", gemini: "Gemini",
    google_aio: "Google AIO", claude: "Claude", copilot: "Copilot",
    grok: "Grok", deepseek: "DeepSeek", meta_ai: "Meta AI",
    sarvam: "Sarvam", krutrim: "Krutrim",
};
function engineName(val: string): string {
    return ENGINE_NAMES[val] || val.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

const CATEGORY_LABELS: Record<string, string> = {
    website_audit: "Website Audit", crawler_analysis: "Crawler Analysis",
    content_gap: "Content Gaps", content_rewrite: "Content Rewrites",
    engine_optimization: "Engine Optimization", best_practice: "Quick Wins",
};

export default function ActionCenterPage() {
    const { brand, loading: brandLoading } = useBrand();
    const { generating, progress, data, startGeneration, loadActions, setData } = useActions();
    const [loading, setLoading] = useState(!data);
    const [verifying, setVerifying] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState<Set<string>>(new Set());
    const [filter, setFilter] = useState<string>("all");
    const loadedBrandRef = useRef<string | null>(null);

    useEffect(() => {
        if (!brand) return;
        // If we already loaded for this brand (context has data), skip
        if (loadedBrandRef.current === brand.id) { setLoading(false); return; }
        setLoading(true);
        loadActions(brand.id).finally(() => {
            loadedBrandRef.current = brand.id;
            setLoading(false);
        });
    }, [brand, loadActions]);

    async function handleGenerate() {
        if (!brand || generating) return;
        startGeneration(brand.id);
    }

    async function handleStatusChange(actionId: string, status: string) {
        if (!brand) return;
        try {
            const updated = await updateActionStatus(brand.id, actionId, status);
            setData(prev => {
                if (!prev) return prev;
                const actions = prev.actions.map(a => a.id === actionId ? updated : a);
                const pending = actions.filter(a => a.status === "pending").length;
                const completed = actions.filter(a => a.status === "completed").length;
                return { ...prev, actions, pending, completed };
            });
        } catch { /* ignore */ }
    }

    function toggleExpand(id: string) {
        setExpanded(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    }

    async function handleVerify(actionId: string) {
        if (!brand || verifying.has(actionId)) return;
        setVerifying(prev => new Set(prev).add(actionId));
        try {
            const updated = await verifyAction(brand.id, actionId);
            setData(prev => {
                if (!prev) return prev;
                const actions = prev.actions.map(a => a.id === actionId ? updated : a);
                return { ...prev, actions };
            });
        } catch { /* ignore */ }
        setVerifying(prev => { const next = new Set(prev); next.delete(actionId); return next; });
    }

    if (brandLoading) return <div style={{ padding: "2rem", color: "var(--muted-foreground)" }}>Loading…</div>;
    if (!brand) return <div style={{ padding: "2rem" }}>No brand set up. <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>Set up →</a></div>;

    const actions = data?.actions ?? [];
    const filtered = filter === "all" ? actions : actions.filter(a => a.status === filter);

    const pendingCount = actions.filter(a => a.status === "pending").length;
    const completedCount = actions.filter(a => a.status === "completed").length;
    const inProgressCount = actions.filter(a => a.status === "in_progress").length;

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <div>
                    <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.25rem" }}>Action Center</h1>
                    <p style={{ color: "var(--muted-foreground)", marginBottom: "1.5rem" }}>
                        AI-generated optimization actions prioritized by impact — fix these to improve your brand visibility
                    </p>
                </div>
                <button onClick={handleGenerate} disabled={generating} style={btnPrimary}>
                    {generating ? "Generating…" : data?.actions.length ? "Refresh Actions" : "Generate Actions"}
                </button>
            </div>

            {/* Generation progress bar */}
            {generating && progress && (
                <div style={{ ...cardStyle, marginBottom: "1.5rem", background: "var(--primary-muted)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                        <span style={{ fontSize: "1.2rem" }}>{PROGRESS_ICONS[progress.step] || "⏳"}</span>
                        <div style={{ flex: 1 }}>
                            <p style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.15rem" }}>{progress.stage}</p>
                            <p style={{ fontSize: "0.7rem", color: "var(--muted-foreground)" }}>{progress.detail || `Step ${progress.step} of ${progress.total_steps}`}</p>
                        </div>
                        {progress.actions_so_far > 0 && (
                            <span style={{ fontSize: "0.75rem", color: "var(--muted-foreground)" }}>{progress.actions_so_far} actions found</span>
                        )}
                    </div>
                    <div style={{ height: 6, borderRadius: 3, background: "var(--border)", overflow: "hidden" }}>
                        <div style={{
                            height: "100%", borderRadius: 3, background: "var(--primary)",
                            width: `${Math.max(5, (progress.step / progress.total_steps) * 100)}%`,
                            transition: "width 0.5s ease",
                        }} />
                    </div>
                </div>
            )}

            {/* Summary: status + category breakdown */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1rem", marginBottom: "2rem" }}>
                {/* Status counts */}
                <div style={{ ...cardStyle, display: "flex", justifyContent: "space-around", alignItems: "center" }}>
                    <SummaryCard label="To Do" value={pendingCount} color="var(--danger)" />
                    <SummaryCard label="In Progress" value={inProgressCount} color="var(--warning)" />
                    <SummaryCard label="Done" value={completedCount} color="var(--success)" />
                </div>
                {/* Category breakdown */}
                <div style={cardStyle}>
                    <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
                        {actions.length} Actions by Category
                    </p>
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        {Object.entries(
                            actions.reduce<Record<string, number>>((acc, a) => { acc[a.category] = (acc[a.category] || 0) + 1; return acc; }, {})
                        ).map(([cat, count]) => (
                            <span key={cat} style={{
                                display: "inline-flex", alignItems: "center", gap: "0.35rem",
                                padding: "0.3rem 0.6rem", borderRadius: "var(--radius-sm)",
                                background: "var(--background)", border: "1px solid var(--border)",
                                fontSize: "0.75rem", fontWeight: 500,
                            }}>
                                {CATEGORY_ICONS[cat] || "📋"} {CATEGORY_LABELS[cat] || cat} <strong>{count}</strong>
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Filter tabs */}
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
                {[["all", "All"], ["pending", "To Do"], ["in_progress", "In Progress"], ["completed", "Done"], ["dismissed", "Dismissed"]].map(([key, label]) => (
                    <button key={key} onClick={() => setFilter(key)}
                        style={{
                            padding: "0.4rem 0.75rem", borderRadius: "var(--radius-sm)", fontSize: "0.8rem", fontWeight: 500,
                            border: "1px solid " + (filter === key ? "var(--primary)" : "var(--border)"),
                            background: filter === key ? "var(--primary-muted)" : "transparent",
                            color: filter === key ? "var(--primary)" : "var(--muted-foreground)",
                            cursor: "pointer",
                        }}
                    >{label}</button>
                ))}
            </div>

            {loading ? (
                <div style={{ color: "var(--muted-foreground)", padding: "3rem", textAlign: "center" }}>Loading actions…</div>
            ) : filtered.length === 0 ? (
                <div style={{ ...cardStyle, textAlign: "center", padding: "3rem", color: "var(--muted-foreground)" }}>
                    {actions.length === 0
                        ? 'No actions yet. Click "Generate Actions" to analyze your brand and create optimization recommendations.'
                        : "No actions match this filter."
                    }
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {filtered.map((action) => (
                        <ActionCard
                            key={action.id}
                            action={action}
                            isExpanded={expanded.has(action.id)}
                            onToggle={() => toggleExpand(action.id)}
                            onStatusChange={handleStatusChange}
                            onVerify={handleVerify}
                            isVerifying={verifying.has(action.id)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div style={cardStyle}>
            <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500, marginBottom: "0.5rem" }}>{label}</p>
            <p style={{ fontSize: "1.75rem", fontWeight: 700, color }}>{value}</p>
        </div>
    );
}

function ActionCard({ action, isExpanded, onToggle, onStatusChange, onVerify, isVerifying }: {
    action: ActionItem;
    isExpanded: boolean;
    onToggle: () => void;
    onStatusChange: (id: string, status: string) => void;
    onVerify: (id: string) => void;
    isVerifying: boolean;
}) {
    const icon = CATEGORY_ICONS[action.category] || "📋";
    const isDone = action.status === "completed" || action.status === "dismissed";
    const canVerify = action.status === "completed" && action.verification_type && action.verification_type !== "manual";
    const vResult = action.verification_status ? VERIFY_LABELS[action.verification_status] : null;

    return (
        <div style={{ ...cardStyle, opacity: isDone ? 0.6 : 1 }}>
            {/* Header */}
            <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", cursor: "pointer" }} onClick={onToggle}>
                <span style={{ fontSize: "1.2rem", flexShrink: 0, marginTop: 2 }}>{icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.25rem" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600, textDecoration: isDone ? "line-through" : "none" }}>{action.title}</span>
                        <span style={badgeStyle(action.status === "completed" ? "var(--success)" : action.status === "in_progress" ? "var(--warning)" : action.status === "dismissed" ? "var(--muted-foreground)" : "var(--primary)")}>
                            {STATUS_LABELS[action.status] || action.status}
                        </span>
                        {vResult && (
                            <span style={badgeStyle(vResult.color)}>{vResult.label}{action.baseline_value != null && action.verified_value != null ? ` ${action.baseline_value} → ${action.verified_value}` : ""}</span>
                        )}
                    </div>
                    <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", lineHeight: 1.5 }}>{action.description}</p>
                    <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", fontSize: "0.7rem", flexWrap: "wrap" }}>
                        <span>Impact: <strong style={{ color: IMPACT_COLORS[action.impact] || "var(--foreground)" }}>{action.impact}</strong></span>
                        <span>Effort: <strong style={{ color: EFFORT_COLORS[action.effort] || "var(--foreground)" }}>{action.effort}</strong></span>
                        {action.current_mention_rate !== undefined && action.current_mention_rate !== null && (
                            <span>Current: <strong>{action.current_mention_rate}%</strong> mention rate</span>
                        )}
                        {action.engine && (
                            <span>Engine: <strong>{engineName(action.engine)}</strong></span>
                        )}
                        {action.verification_type && (
                            <span style={{ color: "var(--muted-foreground)" }}>Verify via: {action.verification_type.replace("_", " ")}</span>
                        )}
                    </div>
                </div>
                <span style={{ fontSize: "1rem", color: "var(--muted-foreground)", flexShrink: 0 }}>{isExpanded ? "▾" : "▸"}</span>
            </div>

            {/* Expanded content */}
            {isExpanded && (
                <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
                    {/* Engine breakdown for content gaps */}
                    {action.engines_missing && action.engines_missing.length > 0 && (
                        <div style={{ marginBottom: "1rem" }}>
                            <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Engine Breakdown</p>
                            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                {action.engines_missing.map(e => (
                                    <span key={e} style={{ ...badgeStyle("var(--danger)"), fontSize: "0.7rem" }}>✗ {engineName(e)}</span>
                                ))}
                                {action.engines_citing?.map(e => (
                                    <span key={e} style={{ ...badgeStyle("var(--success)"), fontSize: "0.7rem" }}>✓ {engineName(e)}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Suggested content */}
                    {action.suggested_content && (
                        <div style={{ marginBottom: "1rem" }}>
                            <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
                                {action.category === "website_audit" ? "Recommended Action" : "Suggested Content"}
                            </p>
                            <div style={{ background: "var(--background)", borderRadius: "var(--radius-sm)", padding: "1rem", fontSize: "0.8rem", lineHeight: 1.7, border: "1px solid var(--border)", whiteSpace: "pre-wrap" }}>
                                {action.suggested_content}
                            </div>
                        </div>
                    )}

                    {/* Suggested schema */}
                    {action.suggested_schema && (
                        <div style={{ marginBottom: "1rem" }}>
                            <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Schema Template</p>
                            <pre style={{ background: "var(--background)", borderRadius: "var(--radius-sm)", padding: "1rem", fontSize: "0.75rem", lineHeight: 1.5, border: "1px solid var(--border)", overflow: "auto", maxHeight: 200 }}>
                                {action.suggested_schema}
                            </pre>
                        </div>
                    )}

                    {/* Prompt context */}
                    {action.prompt_text && (
                        <div style={{ marginBottom: "1rem" }}>
                            <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Target Prompt</p>
                            <p style={{ fontSize: "0.8rem", color: "var(--foreground)" }}>&ldquo;{action.prompt_text}&rdquo;</p>
                        </div>
                    )}

                    {/* Verification result */}
                    {action.verified_at && vResult && (
                        <div style={{ marginBottom: "1rem", padding: "0.75rem 1rem", borderRadius: "var(--radius-sm)", background: `${vResult.color}10`, border: `1px solid ${vResult.color}30` }}>
                            <p style={{ fontSize: "0.8rem", fontWeight: 600, color: vResult.color, marginBottom: "0.25rem" }}>
                                {vResult.label}{action.baseline_value != null && action.verified_value != null ? `: ${action.baseline_value} → ${action.verified_value}` : ""}
                            </p>
                            <p style={{ fontSize: "0.7rem", color: "var(--muted-foreground)" }}>
                                Verified {new Date(action.verified_at).toLocaleString()}
                            </p>
                        </div>
                    )}

                    {/* Status actions */}
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        {action.status !== "in_progress" && action.status !== "completed" && (
                            <button onClick={() => onStatusChange(action.id, "in_progress")} style={btnSmall}>Start</button>
                        )}
                        {action.status !== "completed" && (
                            <button onClick={() => onStatusChange(action.id, "completed")} style={btnSmallSuccess}>Mark Done</button>
                        )}
                        {canVerify && (
                            <button onClick={() => onVerify(action.id)} disabled={isVerifying} style={{ ...btnSmall, borderColor: "var(--success)", color: "var(--success)" }}>
                                {isVerifying ? "Verifying…" : action.verified_at ? "Re-verify" : "Verify Fix"}
                            </button>
                        )}
                        {action.status !== "dismissed" && action.status !== "completed" && (
                            <button onClick={() => onStatusChange(action.id, "dismissed")} style={btnSmallMuted}>Dismiss</button>
                        )}
                        {(action.status === "completed" || action.status === "dismissed") && (
                            <button onClick={() => onStatusChange(action.id, "pending")} style={btnSmallMuted}>Reopen</button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function badgeStyle(color: string): React.CSSProperties {
    return {
        padding: "0.1rem 0.4rem", borderRadius: "var(--radius-xs)", fontSize: "0.65rem",
        fontWeight: 600, background: `${color}20`, color,
    };
}

const cardStyle: React.CSSProperties = { background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "1.25rem" };
const btnPrimary: React.CSSProperties = { padding: "0.6rem 1.25rem", borderRadius: "var(--radius-sm)", border: "none", background: "var(--primary)", color: "#fff", fontWeight: 600, fontSize: "0.875rem", cursor: "pointer" };
const btnSmall: React.CSSProperties = { padding: "0.3rem 0.6rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--primary)", background: "transparent", color: "var(--primary)", cursor: "pointer", fontSize: "0.75rem", fontWeight: 500 };
const btnSmallSuccess: React.CSSProperties = { padding: "0.3rem 0.6rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--success)", background: "transparent", color: "var(--success)", cursor: "pointer", fontSize: "0.75rem", fontWeight: 500 };
const btnSmallMuted: React.CSSProperties = { padding: "0.3rem 0.6rem", borderRadius: "var(--radius-xs)", border: "1px solid var(--border)", background: "transparent", color: "var(--muted-foreground)", cursor: "pointer", fontSize: "0.75rem", fontWeight: 500 };
