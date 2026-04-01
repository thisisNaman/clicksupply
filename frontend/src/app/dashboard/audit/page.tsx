"use client";

import { useState } from "react";

export default function AuditPage() {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<Record<string, unknown> | null>(null);

    async function handleAudit() {
        if (!url) return;
        setLoading(true);
        setResult(null);
        try {
            const resp = await fetch("/api/v1/aeo/audit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });
            if (resp.ok) {
                setResult(await resp.json());
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                AEO Audit
            </h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Audit any page for AI readiness — content structure, schema markup, trust signals
            </p>

            <div
                style={{
                    display: "flex",
                    gap: "0.75rem",
                    marginBottom: "2rem",
                }}
            >
                <input
                    type="url"
                    placeholder="https://example.com/page-to-audit"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAudit()}
                    style={{
                        flex: 1,
                        padding: "0.75rem 1rem",
                        borderRadius: "8px",
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
                        borderRadius: "8px",
                        background: "var(--primary)",
                        color: "white",
                        border: "none",
                        fontWeight: 600,
                        cursor: loading ? "wait" : "pointer",
                        opacity: loading || !url ? 0.6 : 1,
                    }}
                >
                    {loading ? "Auditing..." : "Run Audit"}
                </button>
            </div>

            {result && (
                <div
                    style={{
                        background: "var(--card)",
                        borderRadius: "12px",
                        border: "1px solid var(--border)",
                        padding: "1.5rem",
                    }}
                >
                    <h2 style={{ fontWeight: 600, marginBottom: "1rem" }}>
                        Audit Results — Score: {(result as { overall_score?: number }).overall_score ?? "N/A"}/100
                    </h2>
                    <pre
                        style={{
                            fontSize: "0.8rem",
                            overflow: "auto",
                            maxHeight: "500px",
                            whiteSpace: "pre-wrap",
                        }}
                    >
                        {JSON.stringify(result, null, 2)}
                    </pre>
                </div>
            )}

            {!result && (
                <div
                    style={{
                        background: "var(--card)",
                        borderRadius: "12px",
                        border: "1px solid var(--border)",
                        padding: "2rem",
                        minHeight: "200px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--muted-foreground)",
                    }}
                >
                    Enter a URL above to audit its AI readiness.
                </div>
            )}
        </div>
    );
}
