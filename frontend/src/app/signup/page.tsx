"use client";

import { useState } from "react";
import { signup } from "@/lib/api";

export default function SignupPage() {
    const [form, setForm] = useState({
        full_name: "",
        email: "",
        password: "",
        organization_name: "",
        consent_given: false,
    });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    function update(field: string, value: string | boolean) {
        setForm((prev) => ({ ...prev, [field]: value }));
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");

        if (!form.consent_given) {
            setError("You must consent to data processing to create an account.");
            return;
        }

        setLoading(true);
        try {
            await signup(form);
            window.location.href = "/dashboard/setup";
        } catch (err) {
            setError(err instanceof Error ? err.message : "Signup failed");
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
                    Create your account
                </h1>
                <p style={{ color: "var(--muted-foreground)", fontSize: "0.9rem", margin: 0 }}>
                    Get started with ClickSupply
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
                    Full Name
                    <input
                        type="text"
                        required
                        value={form.full_name}
                        onChange={(e) => update("full_name", e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <label style={labelStyle}>
                    Email
                    <input
                        type="email"
                        required
                        value={form.email}
                        onChange={(e) => update("email", e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <label style={labelStyle}>
                    Password
                    <input
                        type="password"
                        required
                        minLength={8}
                        value={form.password}
                        onChange={(e) => update("password", e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <label style={labelStyle}>
                    Organization Name
                    <input
                        type="text"
                        required
                        value={form.organization_name}
                        onChange={(e) => update("organization_name", e.target.value)}
                        style={inputStyle}
                    />
                </label>

                <label
                    style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.5rem",
                        fontSize: "0.85rem",
                        color: "var(--foreground)",
                        cursor: "pointer",
                    }}
                >
                    <input
                        type="checkbox"
                        checked={form.consent_given}
                        onChange={(e) => update("consent_given", e.target.checked)}
                        style={{ marginTop: 3 }}
                    />
                    <span>
                        I consent to the processing of my personal data in accordance with the
                        Digital Personal Data Protection Act (DPDPA).
                    </span>
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
                    {loading ? "Creating account…" : "Sign up"}
                </button>

                <p
                    style={{
                        textAlign: "center",
                        fontSize: "0.85rem",
                        color: "var(--muted-foreground)",
                        margin: 0,
                    }}
                >
                    Already have an account?{" "}
                    <a href="/login" style={{ color: "var(--primary)" }}>
                        Log in
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
