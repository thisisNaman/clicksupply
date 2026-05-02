"use client";

import { createContext, useContext, useState, useRef, useCallback, type ReactNode } from "react";
import {
    generateActions, streamGenerationProgress, getActions,
    type ActionsResponse, type GenerationProgress,
} from "@/lib/api";

interface ActionContextValue {
    generating: boolean;
    progress: GenerationProgress | null;
    data: ActionsResponse | null;
    startGeneration: (brandId: string) => Promise<void>;
    loadActions: (brandId: string) => Promise<void>;
    setData: (updater: (prev: ActionsResponse | null) => ActionsResponse | null) => void;
}

const ActionContext = createContext<ActionContextValue | null>(null);

export function ActionProvider({ children }: { children: ReactNode }) {
    const [generating, setGenerating] = useState(false);
    const [progress, setProgress] = useState<GenerationProgress | null>(null);
    const [data, setData] = useState<ActionsResponse | null>(null);
    const abortRef = useRef<(() => void) | null>(null);
    const brandIdRef = useRef<string | null>(null);

    const stopStream = useCallback(() => {
        if (abortRef.current) {
            abortRef.current();
            abortRef.current = null;
        }
    }, []);

    const loadActions = useCallback(async (brandId: string) => {
        try {
            const result = await getActions(brandId);
            setData(result);
        } catch {
            // Don't clear existing data on fetch error
        }
    }, []);

    const startGeneration = useCallback(async (brandId: string) => {
        if (generating) return;
        brandIdRef.current = brandId;
        setGenerating(true);
        setProgress({ status: "running", step: 0, total_steps: 6, stage: "Starting…", detail: "", actions_so_far: 0 });

        try {
            const resp = await generateActions(brandId);
            if (resp.status === "already_running" || resp.status === "started") {
                // Subscribe to SSE stream — no polling
                stopStream();
                abortRef.current = streamGenerationProgress(
                    brandId,
                    (p) => setProgress(p),
                    async () => {
                        // Stream ended — fetch final actions
                        setGenerating(false);
                        await loadActions(brandId);
                    },
                );
            }
        } catch {
            setGenerating(false);
            setProgress(null);
        }
    }, [generating, stopStream, loadActions]);

    return (
        <ActionContext.Provider value={{ generating, progress, data, startGeneration, loadActions, setData }}>
            {children}
        </ActionContext.Provider>
    );
}

export function useActions() {
    const ctx = useContext(ActionContext);
    if (!ctx) throw new Error("useActions must be used within ActionProvider");
    return ctx;
}
