"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const fadeUp = {
    hidden: { opacity: 0, y: 30 },
    visible: (i: number) => ({
        opacity: 1,
        y: 0,
        transition: { delay: i * 0.12, duration: 0.5, ease: "easeOut" as const },
    }),
};

const features = [
    {
        icon: "📊",
        title: "Share of Model",
        desc: "Track how often AI engines mention your brand vs competitors across ChatGPT, Gemini, Perplexity & more.",
    },
    {
        icon: "🔍",
        title: "AEO Audit",
        desc: "Deep-scan any page for AI readiness — content structure, schema markup, trust signals — scored 0-100.",
    },
    {
        icon: "🤖",
        title: "Agent Analytics",
        desc: "Ingest server logs to see which AI crawlers visit your site, their error rates, and top paths.",
    },
    {
        icon: "⚡",
        title: "Action Center",
        desc: "AI-generated prioritized actions: website fixes, content gaps, schema suggestions, and quick wins.",
    },
    {
        icon: "📈",
        title: "Visibility Trends",
        desc: "Track mention rate, average position, and sentiment across engines over 7/30/90 day windows.",
    },
    {
        icon: "🏆",
        title: "Competitive Benchmark",
        desc: "See how your brand stacks up against competitors on SoM, mentions, position, and sentiment.",
    },
];

export default function LandingPage() {
    return (
        <div style={{ minHeight: "100vh", overflow: "hidden" }}>
            {/* Nav */}
            <motion.nav
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "1.25rem 3rem",
                    borderBottom: "1px solid var(--border)",
                    backdropFilter: "blur(12px)",
                    position: "sticky",
                    top: 0,
                    zIndex: 50,
                    background: "rgba(9,9,11,0.8)",
                }}
            >
                <span
                    style={{
                        fontSize: "1.35rem",
                        fontWeight: 800,
                        background: "var(--gradient-primary)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                        letterSpacing: "-0.03em",
                    }}
                >
                    ClickSupply
                </span>
                <div style={{ display: "flex", gap: "0.75rem" }}>
                    <Link
                        href="/login"
                        style={{
                            padding: "0.5rem 1.25rem",
                            borderRadius: 8,
                            border: "1px solid var(--border)",
                            color: "var(--foreground)",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            fontWeight: 500,
                        }}
                    >
                        Log in
                    </Link>
                    <Link
                        href="/signup"
                        style={{
                            padding: "0.5rem 1.25rem",
                            borderRadius: 8,
                            border: "none",
                            background: "var(--gradient-primary)",
                            color: "#fff",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            fontWeight: 600,
                        }}
                    >
                        Get Started
                    </Link>
                </div>
            </motion.nav>

            {/* Hero */}
            <section
                style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    textAlign: "center",
                    padding: "6rem 2rem 4rem",
                    position: "relative",
                }}
            >
                {/* Glow orb */}
                <div
                    style={{
                        position: "absolute",
                        top: "-120px",
                        width: 500,
                        height: 500,
                        borderRadius: "50%",
                        background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
                        filter: "blur(60px)",
                        pointerEvents: "none",
                    }}
                />

                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.6 }}
                    style={{
                        display: "inline-block",
                        padding: "0.35rem 1rem",
                        borderRadius: 20,
                        border: "1px solid var(--border-light)",
                        fontSize: "0.8rem",
                        color: "var(--primary)",
                        fontWeight: 500,
                        marginBottom: "1.5rem",
                        background: "var(--primary-muted)",
                    }}
                >
                    AEO / GEO Platform for the AI era
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    style={{
                        fontSize: "clamp(2.5rem, 5vw, 4rem)",
                        fontWeight: 800,
                        letterSpacing: "-0.04em",
                        lineHeight: 1.1,
                        maxWidth: 800,
                        marginBottom: "1.25rem",
                    }}
                >
                    Make your brand visible to{" "}
                    <span
                        style={{
                            background: "var(--gradient-primary)",
                            WebkitBackgroundClip: "text",
                            WebkitTextFillColor: "transparent",
                        }}
                    >
                        AI engines
                    </span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.25 }}
                    style={{
                        fontSize: "1.15rem",
                        color: "var(--muted-foreground)",
                        maxWidth: 580,
                        lineHeight: 1.6,
                        marginBottom: "2.5rem",
                    }}
                >
                    Track your Share of Model across ChatGPT, Gemini, Perplexity & Claude.
                    Get actionable recommendations to boost your brand&apos;s AI visibility.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.35 }}
                    style={{ display: "flex", gap: "1rem" }}
                >
                    <Link
                        href="/signup"
                        style={{
                            padding: "0.75rem 2rem",
                            borderRadius: 10,
                            background: "var(--gradient-primary)",
                            color: "#fff",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1rem",
                            boxShadow: "0 4px 20px rgba(99,102,241,0.3)",
                        }}
                    >
                        Start Free →
                    </Link>
                    <Link
                        href="/dashboard"
                        style={{
                            padding: "0.75rem 2rem",
                            borderRadius: 10,
                            border: "1px solid var(--border-light)",
                            color: "var(--foreground)",
                            textDecoration: "none",
                            fontWeight: 500,
                            fontSize: "1rem",
                        }}
                    >
                        View Demo
                    </Link>
                </motion.div>

                {/* Floating stat pills */}
                <div style={{ position: "relative", width: "100%", maxWidth: 900, height: 80, marginTop: "3rem" }}>
                    {[
                        { label: "5 AI Engines", x: "10%", delay: 0.5 },
                        { label: "AEO Score 0-100", x: "38%", delay: 0.65 },
                        { label: "Real-time Crawlers", x: "68%", delay: 0.8 },
                    ].map((pill) => (
                        <motion.div
                            key={pill.label}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: pill.delay, duration: 0.5, ease: "easeOut" }}
                            style={{
                                position: "absolute",
                                left: pill.x,
                                padding: "0.5rem 1rem",
                                borderRadius: 10,
                                background: "var(--card)",
                                border: "1px solid var(--border)",
                                fontSize: "0.8rem",
                                fontWeight: 600,
                                whiteSpace: "nowrap",
                                boxShadow: "var(--shadow-md)",
                            }}
                        >
                            {pill.label}
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Features grid */}
            <section style={{ padding: "4rem 3rem 5rem", maxWidth: 1200, margin: "0 auto" }}>
                <motion.h2
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    style={{
                        textAlign: "center",
                        fontSize: "1.75rem",
                        fontWeight: 700,
                        marginBottom: "0.5rem",
                        letterSpacing: "-0.02em",
                    }}
                >
                    Everything you need for AI visibility
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    style={{
                        textAlign: "center",
                        color: "var(--muted-foreground)",
                        marginBottom: "3rem",
                        fontSize: "1rem",
                    }}
                >
                    One platform to monitor, audit, and optimize how AI models talk about your brand.
                </motion.p>

                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                        gap: "1.25rem",
                    }}
                >
                    {features.map((f, i) => (
                        <motion.div
                            key={f.title}
                            custom={i}
                            initial="hidden"
                            whileInView="visible"
                            viewport={{ once: true, margin: "-40px" }}
                            variants={fadeUp}
                            whileHover={{ y: -4, borderColor: "var(--border-light)" }}
                            style={{
                                padding: "1.75rem",
                                borderRadius: 14,
                                background: "var(--card)",
                                border: "1px solid var(--border)",
                                transition: "border-color 0.2s",
                            }}
                        >
                            <span style={{ fontSize: "1.75rem", display: "block", marginBottom: "0.75rem" }}>
                                {f.icon}
                            </span>
                            <h3
                                style={{
                                    fontSize: "1.05rem",
                                    fontWeight: 700,
                                    marginBottom: "0.5rem",
                                    letterSpacing: "-0.01em",
                                }}
                            >
                                {f.title}
                            </h3>
                            <p style={{ fontSize: "0.875rem", color: "var(--muted-foreground)", lineHeight: 1.6 }}>
                                {f.desc}
                            </p>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* CTA */}
            <section
                style={{
                    padding: "4rem 2rem",
                    textAlign: "center",
                    borderTop: "1px solid var(--border)",
                }}
            >
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                >
                    <h2 style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "1rem" }}>
                        Ready to own your AI narrative?
                    </h2>
                    <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem", maxWidth: 500, margin: "0 auto 2rem" }}>
                        Join brands that are already optimizing their visibility across AI answer engines.
                    </p>
                    <Link
                        href="/signup"
                        style={{
                            display: "inline-block",
                            padding: "0.85rem 2.5rem",
                            borderRadius: 10,
                            background: "var(--gradient-primary)",
                            color: "#fff",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1.05rem",
                            boxShadow: "0 4px 24px rgba(99,102,241,0.35)",
                        }}
                    >
                        Get Started Free
                    </Link>
                </motion.div>
            </section>

            {/* Footer */}
            <footer
                style={{
                    padding: "2rem 3rem",
                    borderTop: "1px solid var(--border)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "0.8rem",
                    color: "var(--muted-foreground)",
                }}
            >
                <span>© 2026 ClickSupply. All rights reserved.</span>
                <span>AEO/GEO Platform</span>
            </footer>
        </div>
    );
}
