"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { getToken, getMe, logout, autoLogin, type UserInfo } from "@/lib/api";
import { CaptureProvider, useCapture } from "@/lib/capture-context";

export default function DashboardLayout({
    children,
}: {
    children: ReactNode;
}) {
    const [user, setUser] = useState<UserInfo | null>(null);
    const [checked, setChecked] = useState(false);

    useEffect(() => {
        autoLogin()
            .then(() => getMe())
            .then(setUser)
            .finally(() => setChecked(true));
    }, []);

    if (!checked) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
                Loading…
            </div>
        );
    }

    return (
        <CaptureProvider>
            <div style={{ display: "flex", minHeight: "100vh" }}>
                {/* Sidebar */}
                <nav
                    style={{
                        width: "250px",
                        background: "var(--card)",
                        borderRight: "1px solid var(--border)",
                        padding: "1.5rem 1rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.25rem",
                    }}
                >
                    <div
                        style={{
                            fontSize: "1.25rem",
                            fontWeight: 700,
                            color: "var(--primary)",
                            marginBottom: "1.5rem",
                            paddingLeft: "0.75rem",
                        }}
                    >
                        ClickSupply
                    </div>

                    <NavItem href="/dashboard" label="Overview" />
                    <NavItem href="/dashboard/visibility" label="Visibility Scores" />
                    <NavItem href="/dashboard/som" label="Share of Model" />
                    <NavItem href="/dashboard/crawlers" label="Agent Analytics" />
                    <NavItem href="/dashboard/audit" label="AEO Audit" />
                    <NavItem href="/dashboard/prompts" label="Prompt Volumes" />
                    <NavItem href="/dashboard/competitors" label="Competitors" />

                    <div style={{ height: 1, background: "var(--border)", margin: "0.75rem 0" }} />

                    <NavItem href="/dashboard/setup" label="Brand Setup" />
                    <NavItem href="/dashboard/settings" label="Settings" />

                    <div
                        style={{
                            marginTop: "auto",
                            padding: "0.75rem",
                            fontSize: "0.8rem",
                            color: "var(--muted-foreground)",
                            display: "flex",
                            flexDirection: "column",
                            gap: "0.5rem",
                        }}
                    >
                        {user && (
                            <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {user.full_name}
                            </div>
                        )}
                        <button
                            onClick={() => logout()}
                            style={{
                                background: "none",
                                border: "1px solid var(--border)",
                                borderRadius: 6,
                                padding: "0.4rem 0.75rem",
                                fontSize: "0.8rem",
                                cursor: "pointer",
                                color: "var(--foreground)",
                            }}
                        >
                            Log out
                        </button>
                        <div>v0.1.0 — Phase 1</div>
                    </div>
                </nav>

                {/* Main content */}
                <main style={{ flex: 1, padding: "2rem", overflowY: "auto" }}>
                    <GlobalCaptureBar />
                    {children}
                </main>
            </div>
        </CaptureProvider>
    );
}

function GlobalCaptureBar() {
    const { capturing, progress, cancelCapture } = useCapture();
    if (!capturing || !progress || progress.total_steps === 0) return null;

    const pct = (progress.completed_steps / progress.total_steps) * 100;

    return (
        <div style={{ padding: "1rem 1.25rem", borderRadius: 10, background: "var(--card)", border: "1px solid var(--border)", marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>Capture in progress</span>
                    <span style={{ fontSize: "0.8rem", color: "var(--muted-foreground)" }}>
                        {Math.round(pct)}%
                    </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--muted-foreground)" }}>
                        {progress.completed_steps}/{progress.total_steps} steps
                    </span>
                    <button
                        onClick={cancelCapture}
                        style={{
                            padding: "0.25rem 0.65rem",
                            borderRadius: 6,
                            border: "1px solid var(--border)",
                            background: "transparent",
                            color: "var(--muted-foreground)",
                            fontSize: "0.75rem",
                            cursor: "pointer",
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </div>
            <div style={{ width: "100%", height: 8, borderRadius: 4, background: "var(--muted)", overflow: "hidden", marginBottom: "0.5rem" }}>
                <div style={{ height: "100%", borderRadius: 4, background: "var(--primary)", width: `${pct}%`, transition: "width 0.3s ease" }} />
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--muted-foreground)", margin: 0 }}>
                {progress.current_engine && progress.current_prompt
                    ? `${progress.current_engine} — "${progress.current_prompt}"`
                    : "Starting…"
                }
            </p>
            <p style={{ fontSize: "0.75rem", color: "var(--muted-foreground)", margin: "0.25rem 0 0" }}>
                {progress.responses_captured} captured · {progress.errors} errors
            </p>
        </div>
    );
}

function NavItem({ href, label }: { href: string; label: string }) {
    const pathname = usePathname();
    const isActive = href === "/dashboard" ? pathname === href : pathname.startsWith(href);

    return (
        <Link
            href={href}
            style={{
                padding: "0.6rem 0.75rem",
                borderRadius: "6px",
                color: isActive ? "var(--primary)" : "var(--foreground)",
                background: isActive ? "var(--background)" : "transparent",
                textDecoration: "none",
                fontSize: "0.9rem",
                fontWeight: isActive ? 600 : 400,
                transition: "background 0.15s, color 0.15s",
            }}
        >
            {label}
        </Link>
    );
}
