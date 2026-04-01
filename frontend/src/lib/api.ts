const API_BASE = "/api/v1";

// ──── Token helpers ────

const TOKEN_KEY = "clicksupply_token";

// Default test user — bypasses login/signup UI
const DEFAULT_EMAIL = "test@test.com";
const DEFAULT_PASSWORD = "test12345";
export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
}

// ──── API client ────

interface ApiOptions {
    method?: string;
    body?: unknown;
    token?: string;
    auth?: boolean; // default true — auto-attach stored JWT
}

export async function api<T = unknown>(
    path: string,
    options: ApiOptions = {}
): Promise<T> {
    const { method = "GET", body, token, auth = true } = options;
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };
    const jwt = token ?? (auth ? getToken() : null);
    if (jwt) {
        headers["Authorization"] = `Bearer ${jwt}`;
    }
    const res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) {
        removeToken();
        await autoLogin();
        throw new Error("Session expired — retrying login");
    }
    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || "API error");
    }
    return res.json();
}

// ──── Auth API ────

export interface AuthToken {
    access_token: string;
    token_type: string;
}

export interface UserInfo {
    id: string;
    email: string;
    full_name: string;
    role: string;
    organization_id: string;
    is_active: boolean;
}

export async function signup(data: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
    consent_given: boolean;
}): Promise<AuthToken> {
    const result = await api<AuthToken>("/auth/signup", {
        method: "POST",
        body: data,
        auth: false,
    });
    setToken(result.access_token);
    return result;
}

export async function login(email: string, password: string): Promise<AuthToken> {
    const result = await api<AuthToken>("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
    });
    setToken(result.access_token);
    return result;
}

export async function getMe(): Promise<UserInfo> {
    return api<UserInfo>("/auth/me");
}

export function logout(): void {
    removeToken();
    if (typeof window !== "undefined") {
        window.location.href = "/dashboard";
    }
}

// ──── Brand API ────

export interface Brand {
    id: string;
    name: string;
    domain: string | null;
    aliases: Record<string, string> | null;
    industry: string | null;
    created_at: string;
}

export interface Competitor {
    id: string;
    name: string;
    domain: string | null;
}

export interface TrackedPrompt {
    id: string;
    text: string;
    language: string;
    region: string;
    is_active: boolean;
    created_at: string;
}

export async function createBrand(data: {
    name: string;
    domain?: string;
    industry?: string;
}): Promise<Brand> {
    return api<Brand>("/brands", { method: "POST", body: data });
}

export async function listBrands(): Promise<Brand[]> {
    return api<Brand[]>("/brands");
}

export async function updateBrand(
    brandId: string,
    data: { name?: string; domain?: string; industry?: string }
): Promise<Brand> {
    return api<Brand>(`/brands/${brandId}`, { method: "PUT", body: data });
}

export async function deleteBrand(brandId: string): Promise<void> {
    await api(`/brands/${brandId}`, { method: "DELETE" });
}

export async function addCompetitor(
    brandId: string,
    data: { name: string; domain?: string }
): Promise<Competitor> {
    return api<Competitor>(`/brands/${brandId}/competitors`, {
        method: "POST",
        body: data,
    });
}

export async function listCompetitors(brandId: string): Promise<Competitor[]> {
    return api<Competitor[]>(`/brands/${brandId}/competitors`);
}

export async function addPrompt(
    brandId: string,
    data: { text: string; language?: string; region?: string }
): Promise<TrackedPrompt> {
    return api<TrackedPrompt>(`/brands/${brandId}/prompts`, {
        method: "POST",
        body: data,
    });
}

export async function listPrompts(brandId: string): Promise<TrackedPrompt[]> {
    return api<TrackedPrompt[]>(`/brands/${brandId}/prompts`);
}

// ──── Analytics API ────

export interface VisibilityScore {
    engine: string;
    date: string;
    share_of_model: number;
    avg_generative_position: number | null;
    mention_count: number;
    total_prompts_run: number;
    positive_sentiment_pct: number;
    negative_sentiment_pct: number;
    neutral_sentiment_pct: number;
    top_citations: Record<string, number> | null;
}

export interface ShareOfModel {
    brand_id: string;
    period_days: number;
    total_responses: number;
    brand_mentioned: number;
    share_of_model: number;
}

export interface CrawlerStats {
    crawler_type: string;
    total_visits: number;
    unique_paths: number;
    avg_response_size: number;
    latest_visit: string | null;
}

export interface SentimentResponse {
    per_engine: { engine: string; positive_pct: number; neutral_pct: number; negative_pct: number; total_responses: number }[];
    top_keywords: { word: string; count: number; sentiment_bias: string }[];
    trend: { date: string; positive_pct: number; neutral_pct: number; negative_pct: number }[];
}

export interface PlatformStat {
    engine: string;
    visibility_score: number;
    avg_position: number | null;
    mention_rate: number;
    sentiment_positive_pct: number;
    citation_count: number;
}

export interface BenchmarkResponse {
    brand: { name: string; domain?: string | null; avg_som: number; avg_position: number | null; mention_count: number; sentiment_positive_pct: number };
    competitors: { name: string; domain?: string | null; avg_som: number; avg_position: number | null; mention_count: number; sentiment_positive_pct: number }[];
    rankings: Record<string, number>;
}

export async function getVisibility(brandId: string, days = 30): Promise<VisibilityScore[]> {
    return api<VisibilityScore[]>(`/analytics/visibility/${brandId}?days=${days}`);
}

export async function getShareOfModel(brandId: string, days = 7): Promise<ShareOfModel> {
    return api<ShareOfModel>(`/analytics/share-of-model/${brandId}?days=${days}`);
}

export async function getCrawlerStats(brandId: string, days = 30): Promise<CrawlerStats[]> {
    return api<CrawlerStats[]>(`/analytics/crawlers/${brandId}?days=${days}`);
}

export async function getSentiment(brandId: string, days = 30): Promise<SentimentResponse> {
    return api<SentimentResponse>(`/analytics/sentiment/${brandId}?days=${days}`);
}

export async function getPlatforms(brandId: string, days = 30): Promise<{ platforms: PlatformStat[] }> {
    return api<{ platforms: PlatformStat[] }>(`/analytics/platforms/${brandId}?days=${days}`);
}

export async function getBenchmark(brandId: string, days = 30): Promise<BenchmarkResponse> {
    return api<BenchmarkResponse>(`/analytics/benchmark/${brandId}?days=${days}`);
}

export async function triggerCapture(brandId: string): Promise<{ status: string; brand_id: string }> {
    return api(`/capture/run`, { method: "POST", body: { brand_id: brandId } });
}

export interface CaptureProgress {
    status: string;
    brand_id: string;
    total_prompts: number;
    total_engines: number;
    completed_steps: number;
    total_steps: number;
    current_prompt: string | null;
    current_engine: string | null;
    prompts_run: number;
    responses_captured: number;
    errors: number;
    scores_computed: number;
    error_message: string | null;
}

export async function getCaptureProgress(brandId: string): Promise<CaptureProgress> {
    return api<CaptureProgress>(`/capture/progress/${brandId}`);
}

export async function cancelCapture(brandId: string): Promise<{ status: string; brand_id: string }> {
    return api(`/capture/cancel/${brandId}`, { method: "POST" });
}

export interface CaptureStatus {
    capture_mode: string;
    analysis_mode: string;
    engines: Record<string, string>;
    available_count: number;
}

export async function getCaptureStatus(): Promise<CaptureStatus> {
    return api<CaptureStatus>(`/capture/status`);
}

// ──── Auto-login with default test user ────

export async function autoLogin(): Promise<void> {
    if (getToken()) return;
    try {
        await login(DEFAULT_EMAIL, DEFAULT_PASSWORD);
    } catch {
        // User may not exist yet — create it then login
        try {
            await signup({
                email: DEFAULT_EMAIL,
                password: DEFAULT_PASSWORD,
                full_name: "Test User",
                organization_name: "Test Org",
                consent_given: true,
            });
        } catch {
            // Already exists, just login
            await login(DEFAULT_EMAIL, DEFAULT_PASSWORD);
        }
    }
}
