"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
    listBrands,
    listCompetitors,
    listPrompts,
    addCompetitor,
    addPrompt,
    updateBrand,
    deleteBrand,
    type Brand,
    type Competitor,
    type TrackedPrompt,
} from "@/lib/api";

export default function SettingsPage() {
    const router = useRouter();
    const [brand, setBrand] = useState<Brand | null>(null);
    const [competitors, setCompetitors] = useState<Competitor[]>([]);
    const [prompts, setPrompts] = useState<TrackedPrompt[]>([]);
    const [loading, setLoading] = useState(true);

    // Edit brand
    const [editing, setEditing] = useState(false);
    const [editName, setEditName] = useState("");
    const [editDomain, setEditDomain] = useState("");
    const [editIndustry, setEditIndustry] = useState("");
    const [saving, setSaving] = useState(false);

    // Delete confirmation
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleting, setDeleting] = useState(false);

    // Add forms
    const [compName, setCompName] = useState("");
    const [compDomain, setCompDomain] = useState("");
    const [promptText, setPromptText] = useState("");

    const loadBrand = useCallback(async () => {
        try {
            const brands = await listBrands();
            if (brands.length > 0) {
                setBrand(brands[0]);
            }
        } catch {
            // ignore
        }
    }, []);

    const loadBrandData = useCallback(async (brandId: string) => {
        setLoading(true);
        try {
            const [c, p] = await Promise.all([
                listCompetitors(brandId),
                listPrompts(brandId),
            ]);
            setCompetitors(c);
            setPrompts(p);
        } catch {
            // ignore
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadBrand();
    }, [loadBrand]);

    useEffect(() => {
        if (brand) {
            loadBrandData(brand.id);
        } else {
            setLoading(false);
        }
    }, [brand, loadBrandData]);

    function startEditing() {
        if (!brand) return;
        setEditName(brand.name);
        setEditDomain(brand.domain || "");
        setEditIndustry(brand.industry || "");
        setEditing(true);
    }

    async function handleSave() {
        if (!brand || !editName.trim()) return;
        setSaving(true);
        try {
            const updated = await updateBrand(brand.id, {
                name: editName.trim(),
                domain: editDomain.trim() || undefined,
                industry: editIndustry.trim() || undefined,
            });
            setBrand(updated);
            setEditing(false);
        } catch {
            // ignore
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete() {
        if (!brand) return;
        setDeleting(true);
        try {
            await deleteBrand(brand.id);
            router.push("/dashboard/setup");
        } catch {
            setDeleting(false);
            setShowDeleteConfirm(false);
        }
    }

    async function handleAddCompetitor() {
        if (!compName.trim() || !brand) return;
        try {
            const c = await addCompetitor(brand.id, {
                name: compName.trim(),
                domain: compDomain.trim() || undefined,
            });
            setCompetitors((prev) => [...prev, c]);
            setCompName("");
            setCompDomain("");
        } catch {
            // ignore
        }
    }

    async function handleAddPrompt() {
        if (!promptText.trim() || !brand) return;
        try {
            const p = await addPrompt(brand.id, { text: promptText.trim() });
            setPrompts((prev) => [...prev, p]);
            setPromptText("");
        } catch {
            // ignore
        }
    }

    if (!brand && !loading) {
        return (
            <div>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                    Settings
                </h1>
                <p style={{ color: "var(--muted-foreground)" }}>
                    No brand set up yet.{" "}
                    <a href="/dashboard/setup" style={{ color: "var(--primary)" }}>
                        Run setup first →
                    </a>
                </p>
            </div>
        );
    }

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                Settings
            </h1>
            <p style={{ color: "var(--muted-foreground)", marginBottom: "2rem" }}>
                Manage your brand, competitors, and tracked prompts
            </p>

            {/* Brand info / edit */}
            {brand && (
                <div style={cardStyle}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                        <h2 style={{ ...cardTitle, margin: 0 }}>Brand</h2>
                        {!editing && (
                            <div style={{ display: "flex", gap: "0.5rem" }}>
                                <button onClick={startEditing} style={btnStyle}>
                                    Edit
                                </button>
                                <button
                                    onClick={() => setShowDeleteConfirm(true)}
                                    style={{ ...btnStyle, background: "#dc2626" }}
                                >
                                    Delete
                                </button>
                            </div>
                        )}
                    </div>

                    {editing ? (
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                            <div>
                                <div style={metaLabel}>Name</div>
                                <input
                                    type="text"
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <div style={metaLabel}>Domain</div>
                                <input
                                    type="text"
                                    value={editDomain}
                                    onChange={(e) => setEditDomain(e.target.value)}
                                    placeholder="example.com"
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <div style={metaLabel}>Industry</div>
                                <input
                                    type="text"
                                    value={editIndustry}
                                    onChange={(e) => setEditIndustry(e.target.value)}
                                    placeholder="e.g. food delivery"
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ gridColumn: "1 / -1", display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                                <button onClick={handleSave} disabled={saving || !editName.trim()} style={btnStyle}>
                                    {saving ? "Saving…" : "Save"}
                                </button>
                                <button onClick={() => setEditing(false)} style={{ ...btnStyle, background: "var(--muted)" }}>
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                            <div>
                                <div style={metaLabel}>Name</div>
                                <div>{brand.name}</div>
                            </div>
                            <div>
                                <div style={metaLabel}>Domain</div>
                                <div>{brand.domain || "—"}</div>
                            </div>
                            <div>
                                <div style={metaLabel}>Industry</div>
                                <div>{brand.industry || "—"}</div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Delete confirmation modal */}
            {showDeleteConfirm && (
                <div style={overlayStyle}>
                    <div style={modalStyle}>
                        <h3 style={{ margin: "0 0 0.75rem", fontSize: "1.1rem", fontWeight: 600 }}>
                            Delete Brand
                        </h3>
                        <p style={{ margin: "0 0 1.25rem", color: "var(--muted-foreground)", fontSize: "0.9rem" }}>
                            This will permanently delete <strong>{brand?.name}</strong> along with
                            all competitors, tracked prompts, and analytics data. This action
                            cannot be undone.
                        </p>
                        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                disabled={deleting}
                                style={{ ...btnStyle, background: "var(--muted)" }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                style={{ ...btnStyle, background: "#dc2626" }}
                            >
                                {deleting ? "Deleting…" : "Delete Brand"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Competitors */}
            <div style={cardStyle}>
                <h2 style={cardTitle}>Competitors ({competitors.length})</h2>

                <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
                    <input
                        type="text"
                        value={compName}
                        onChange={(e) => setCompName(e.target.value)}
                        placeholder="Name"
                        style={{ ...inputStyle, flex: 1 }}
                        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddCompetitor())}
                    />
                    <input
                        type="text"
                        value={compDomain}
                        onChange={(e) => setCompDomain(e.target.value)}
                        placeholder="domain.com"
                        style={{ ...inputStyle, flex: 1 }}
                        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddCompetitor())}
                    />
                    <button onClick={handleAddCompetitor} style={btnStyle}>
                        Add
                    </button>
                </div>

                {competitors.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>
                        No competitors added yet.
                    </p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={thStyle}>Name</th>
                                <th style={thStyle}>Domain</th>
                            </tr>
                        </thead>
                        <tbody>
                            {competitors.map((c) => (
                                <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={tdStyle}>{c.name}</td>
                                    <td style={tdStyle}>{c.domain || "—"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Prompts */}
            <div style={cardStyle}>
                <h2 style={cardTitle}>Tracked Prompts ({prompts.length})</h2>

                <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
                    <input
                        type="text"
                        value={promptText}
                        onChange={(e) => setPromptText(e.target.value)}
                        placeholder="e.g. Best fintech apps in India"
                        style={{ ...inputStyle, flex: 1 }}
                        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddPrompt())}
                    />
                    <button onClick={handleAddPrompt} style={btnStyle}>
                        Add
                    </button>
                </div>

                {prompts.length === 0 ? (
                    <p style={{ color: "var(--muted-foreground)", fontSize: "0.875rem" }}>
                        No prompts added yet.
                    </p>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                <th style={thStyle}>Prompt</th>
                                <th style={thStyle}>Language</th>
                                <th style={thStyle}>Region</th>
                                <th style={thStyle}>Active</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prompts.map((p) => (
                                <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={tdStyle}>{p.text}</td>
                                    <td style={tdStyle}>{p.language}</td>
                                    <td style={tdStyle}>{p.region}</td>
                                    <td style={tdStyle}>{p.is_active ? "✓" : "✕"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

const inputStyle: React.CSSProperties = {
    padding: "0.65rem 0.75rem",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--background)",
    color: "var(--foreground)",
    fontSize: "0.9rem",
};

const btnStyle: React.CSSProperties = {
    padding: "0.65rem 1rem",
    borderRadius: 8,
    border: "none",
    background: "var(--primary)",
    color: "#fff",
    fontSize: "0.875rem",
    fontWeight: 600,
    cursor: "pointer",
    whiteSpace: "nowrap",
};

const cardStyle: React.CSSProperties = {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 10,
    padding: "1.5rem",
    marginBottom: "1.5rem",
};

const cardTitle: React.CSSProperties = {
    fontSize: "1rem",
    fontWeight: 600,
    margin: "0 0 1rem",
};

const metaLabel: React.CSSProperties = {
    fontSize: "0.8rem",
    color: "var(--muted-foreground)",
    marginBottom: "0.25rem",
};

const thStyle: React.CSSProperties = {
    textAlign: "left",
    padding: "0.5rem 0.75rem",
    fontWeight: 600,
    color: "var(--muted-foreground)",
};

const tdStyle: React.CSSProperties = {
    padding: "0.5rem 0.75rem",
};

const overlayStyle: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.5)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 50,
};

const modalStyle: React.CSSProperties = {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 12,
    padding: "1.5rem",
    maxWidth: 420,
    width: "100%",
};
