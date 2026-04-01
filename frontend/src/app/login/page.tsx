"use client";

import { useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await login(email, password);
            window.location.href = "/dashboard";
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--background)",
            }}
        >
            <form
                onSubmit={handleSubmit}
                style={{
                    width: "100%",
                    maxWidth: 420,
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                    padding: "2.5rem 2rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "1rem",
                }}
            >
                <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                    Welcome back
                </h1>
                <p style={{ color: "var(--muted-foreground)", fontSize: "0.9rem", margin: 0 }}>
                    Log in to ClickSupply
                </p>

                {error && (
                    <div
                        style={{
                            background: "#fef2f2",
                            color: "#b91c1c",
                            padding: "0.75rem 1rem",
                            borderRadius: 8,
                            fontSize: "0.875rem",
                        }}
                    >
                        {error}
                    </div>
                )}

                <label style={labelStyle}>
                    Email
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <label style={labelStyle}>
                    Password
                    <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <button
                    type="submit"
                    disabled={loading}
                    style={{
                        marginTop: "0.5rem",
                        padding: "0.75rem",
                        borderRadius: 8,
                        border: "none",
                        background: "var(--primary)",
                        color: "#fff",
                        fontSize: "0.95rem",
                        fontWeight: 600,
                        cursor: loading ? "wait" : "pointer",
                        opacity: loading ? 0.7 : 1,
                    }}
                >
                    {loading ? "Logging in…" : "Log in"}
                </button>

                <p
                    style={{
                        textAlign: "center",
                        fontSize: "0.85rem",
                        color: "var(--muted-foreground)",
                        margin: 0,
                    }}
                >
                    Don&apos;t have an account?{" "}
                    <a href="/signup" style={{ color: "var(--primary)" }}>
                        Sign up
                    </a>
                </p>
            </form>
        </div>
    );
}

const labelStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "0.35rem",
    fontSize: "0.875rem",
    fontWeight: 500,
    color: "var(--foreground)",
};

const inputStyle: React.CSSProperties = {
    padding: "0.65rem 0.75rem",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--background)",
    color: "var(--foreground)",
    fontSize: "0.9rem",
};
