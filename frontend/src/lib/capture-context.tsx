"use client";

import { createContext, useContext, useState, useRef, useCallback, type ReactNode } from "react";
import { triggerCapture, getCaptureProgress, cancelCapture as apiCancelCapture, type CaptureProgress } from "@/lib/api";

interface CaptureContextValue {
    capturing: boolean;
    progress: CaptureProgress | null;
    captureResult: string | null;
    startCapture: (brandId: string) => Promise<void>;
    cancelCapture: () => Promise<void>;
    resumeIfRunning: (brandId: string) => Promise<void>;
    clearResult: () => void;
}

const CaptureContext = createContext<CaptureContextValue | null>(null);

export function CaptureProvider({ children }: { children: ReactNode }) {
    const [capturing, setCapturing] = useState(false);
    const [progress, setProgress] = useState<CaptureProgress | null>(null);
    const [captureResult, setCaptureResult] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const brandIdRef = useRef<string | null>(null);

    const stopPolling = useCallback(() => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
    }, []);

    const startPolling = useCallback((brandId: string) => {
        stopPolling();
        pollRef.current = setInterval(async () => {
            try {
                const p = await getCaptureProgress(brandId);
                setProgress(p);

                if (p.status === "completed") {
                    stopPolling();
                    setCapturing(false);
                    setCaptureResult(
                        `Captured ${p.responses_captured} responses, ${p.scores_computed} scores computed.${p.errors > 0 ? ` (${p.errors} errors)` : ""}`
                    );
                } else if (p.status === "failed") {
                    stopPolling();
                    setCapturing(false);
                    setCaptureResult(p.error_message || "Capture failed");
                } else if (p.status === "cancelled") {
                    stopPolling();
                    setCapturing(false);
                    setCaptureResult(
                        `Capture cancelled. ${p.responses_captured} responses captured before cancellation.${p.errors > 0 ? ` (${p.errors} errors)` : ""}`
                    );
                }
            } catch {
                // polling error — ignore, retry next interval
            }
        }, 2000);
    }, [stopPolling]);

    const startCapture = useCallback(async (brandId: string) => {
        setCaptureResult(null);
        brandIdRef.current = brandId;

        if (capturing) return;
        setCapturing(true);
        setProgress(null);
        try {
            await triggerCapture(brandId);
            startPolling(brandId);
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Capture failed";
            // If already in progress (429), attach to the running capture
            if (msg.includes("already in progress")) {
                startPolling(brandId);
            } else {
                setCaptureResult(msg);
                setCapturing(false);
            }
        }
    }, [capturing, startPolling]);

    const cancelCapture = useCallback(async () => {
        const brandId = brandIdRef.current;
        if (!brandId) return;
        try {
            await apiCancelCapture(brandId);
            // Polling will pick up "cancelled" status
        } catch {
            // Already finished or not found — just stop
            stopPolling();
            setCapturing(false);
        }
    }, [stopPolling]);

    const resumeIfRunning = useCallback(async (brandId: string) => {
        if (capturing) return; // already tracking
        try {
            const p = await getCaptureProgress(brandId);
            if (p.status === "running") {
                brandIdRef.current = brandId;
                setCapturing(true);
                setProgress(p);
                startPolling(brandId);
            }
        } catch {
            // No capture running — ignore
        }
    }, [capturing, startPolling]);

    const clearResult = useCallback(() => setCaptureResult(null), []);

    return (
        <CaptureContext.Provider value={{ capturing, progress, captureResult, startCapture, cancelCapture, resumeIfRunning, clearResult }}>
            {children}
        </CaptureContext.Provider>
    );
}

export function useCapture(): CaptureContextValue {
    const ctx = useContext(CaptureContext);
    if (!ctx) throw new Error("useCapture must be used within <CaptureProvider>");
    return ctx;
}
