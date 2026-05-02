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
    if (res.status === 401 && auth) {
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
    intent: string | null;
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

export async function updatePrompt(
    brandId: string,
    promptId: string,
    data: { text?: string; language?: string; region?: string; is_active?: boolean }
): Promise<TrackedPrompt> {
    return api<TrackedPrompt>(`/brands/${brandId}/prompts/${promptId}`, {
        method: "PUT",
        body: data,
    });
}

export async function deletePrompt(brandId: string, promptId: string): Promise<void> {
    await api(`/brands/${brandId}/prompts/${promptId}`, { method: "DELETE" });
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

// ──── Intent & Co-Citation Analytics ────

export interface IntentDistribution {
    intent: string;
    count: number;
    pct: number;
}

export interface IntentResponse {
    distribution: IntentDistribution[];
    top_prompts_by_intent: Record<string, { text: string; visibility_pct: number }[]>;
}

export interface CoCitedBrand {
    name: string;
    co_occurrence_count: number;
    platforms: string[];
    avg_sentiment: string;
}

export interface UncitedGap {
    prompt_text: string;
    prompt_id: string;
    competitor_name: string;
    competitor_sentiment: string;
    engines: string[];
}

export interface CoCitationResponse {
    co_cited_brands: CoCitedBrand[];
    total_responses_with_brand: number;
    uncited_gaps: UncitedGap[];
    total_prompts_analyzed: number;
}

export async function getIntentDistribution(brandId: string, days = 30): Promise<IntentResponse> {
    return api<IntentResponse>(`/analytics/intent/${brandId}?days=${days}`);
}

export async function getCoCitations(brandId: string, days = 30): Promise<CoCitationResponse> {
    return api<CoCitationResponse>(`/analytics/co-citations/${brandId}?days=${days}`);
}

// ──── Prompt-Brand Matrix ────

export interface BrandMention {
    name: string;
    engines: string[];
    mention_count: number;
    avg_position: number | null;
    dominant_sentiment: string;
    is_target: boolean;
}

export interface PromptBrandEntry {
    prompt_text: string;
    prompt_id: string;
    intent: string | null;
    brand_mentions: BrandMention[];
}

export interface PromptBrandMatrix {
    prompts: PromptBrandEntry[];
    total_prompts: number;
    brands_found: string[];
}

export async function getPromptBrandMatrix(brandId: string, days = 30): Promise<PromptBrandMatrix> {
    return api<PromptBrandMatrix>(`/analytics/prompt-brands/${brandId}?days=${days}`);
}

// ──── Response Viewer ────

export interface AIResponseDetail {
    id: string;
    engine: string;
    raw_response: string;
    brand_mentioned: boolean;
    generative_position: number | null;
    sentiment: string | null;
    citations: Record<string, unknown> | null;
    extra_metadata: Record<string, unknown> | null;
    captured_at: string;
    cost_usd: number;
    prompt_text: string | null;
    prompt_language: string | null;
    prompt_region: string | null;
}

export async function getResponsesDetail(
    brandId: string,
    opts: { engine?: string; language?: string; region?: string; limit?: number } = {},
): Promise<AIResponseDetail[]> {
    const params = new URLSearchParams();
    if (opts.engine) params.set("engine", opts.engine);
    if (opts.language) params.set("language", opts.language);
    if (opts.region) params.set("region", opts.region);
    if (opts.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return api<AIResponseDetail[]>(`/analytics/responses-detail/${brandId}${qs ? "?" + qs : ""}`);
}

// ──── Trends ────

export interface TrendPoint {
    date: string;
    visibility_score: number;
    mention_count: number;
    avg_position: number | null;
}

export interface TrendsResponse {
    series: TrendPoint[];
}

export async function getTrends(brandId: string, days = 30): Promise<TrendsResponse> {
    return api<TrendsResponse>(`/analytics/trends/${brandId}?days=${days}`);
}

// ──── Citations ────

export interface CitationDomain {
    domain: string;
    count: number;
    engines: string[];
    avg_sentiment: string;
}

export interface CitationResponse {
    top_domains: CitationDomain[];
    total_citations: number;
}

export async function getCitations(brandId: string, days = 30): Promise<CitationResponse> {
    return api<CitationResponse>(`/analytics/citations/${brandId}?days=${days}`);
}

// ──── Topic Clustering ────

export interface TopicPrompt {
    prompt_id: string;
    text: string;
    intent: string | null;
    visibility_pct: number;
    mention_count: number;
}

export interface TopicCluster {
    topic: string;
    prompt_count: number;
    avg_visibility: number;
    avg_position: number | null;
    dominant_intent: string | null;
    prompts: TopicPrompt[];
}

export interface TopicClusterResponse {
    clusters: TopicCluster[];
    total_prompts: number;
    total_topics: number;
}

export async function getTopicClusters(
    brandId: string,
    days = 30,
    opts: { engine?: string; language?: string; region?: string } = {},
): Promise<TopicClusterResponse> {
    const params = new URLSearchParams({ days: String(days) });
    if (opts.engine) params.set("engine", opts.engine);
    if (opts.language) params.set("language", opts.language);
    if (opts.region) params.set("region", opts.region);
    return api<TopicClusterResponse>(`/analytics/topics/${brandId}?${params}`);
}

// ──── Competitive Citations ────

export interface CompetitorCitationDomain {
    domain: string;
    count: number;
    engines: string[];
    avg_sentiment: string;
}

export interface CompetitorCitations {
    competitor_name: string;
    total_citations: number;
    top_domains: CompetitorCitationDomain[];
}

export interface CompetitorCitationsResponse {
    competitors: CompetitorCitations[];
    your_top_domains: CompetitorCitationDomain[];
    overlap_domains: string[];
}

export async function getCompetitiveCitations(brandId: string, days = 30): Promise<CompetitorCitationsResponse> {
    return api<CompetitorCitationsResponse>(`/analytics/competitive-citations/${brandId}?days=${days}`);
}

// ──── Smart Insights ────

export interface InsightItem {
    type: string;
    severity: string;
    title: string;
    description: string;
    action?: string;
    engine?: string;
    metric_before?: number;
    metric_after?: number;
    change_pct?: number;
    examples?: { prompt: string; competitors: string[] }[];
    prompts?: { prompt: string; mention_rate: number; total_responses: number }[];
    top_sources?: { domain: string; count: number }[];
    engine_breakdown?: { engine: string; rate: number; total: number }[];
}

export interface InsightsResponse {
    insights: InsightItem[];
    generated_at: string;
}

export async function getSmartInsights(brandId: string): Promise<InsightsResponse> {
    return api<InsightsResponse>(`/intelligence/insights/${brandId}`);
}

// ──── Brand Health Score ────

export interface HealthPillar {
    score: number;
    weight: number;
    detail: string;
    trend: number;
}

export interface HealthScoreResponse {
    score: number;
    grade: string;
    trend: number;
    period_days: number;
    pillars: Record<string, HealthPillar>;
}

export async function getHealthScore(brandId: string, days = 7): Promise<HealthScoreResponse> {
    return api<HealthScoreResponse>(`/intelligence/health/${brandId}?days=${days}`);
}

// ──── Action Center ────

export interface ActionItem {
    id: string;
    brand_id: string;
    category: string;
    title: string;
    description: string;
    impact: string;
    effort: string;
    action_type: string;
    status: string;
    priority_rank: number;
    created_at: string;
    prompt_text?: string;
    prompt_id?: string;
    current_mention_rate?: number;
    suggested_content?: string;
    suggested_schema?: string;
    engine?: string;
    current_rate?: number;
    updated_at?: string;
    // Verification
    verification_type?: string;
    baseline_value?: number | null;
    verified_at?: string;
    verified_value?: number | null;
    verification_status?: string;
    // Crawler / audit metadata
    crawler_type?: string;
    audit_category?: string;
    audit_severity?: string;
    engines_missing?: string[];
    engines_citing?: string[];
}

export interface ActionsResponse {
    actions: ActionItem[];
    total: number;
    pending: number;
    completed: number;
}

export async function generateActions(brandId: string): Promise<{ status: string; brand_id: string }> {
    return api(`/intelligence/actions/${brandId}/generate`, { method: "POST" });
}

export interface GenerationProgress {
    status: string;  // idle, running, completed, failed
    step: number;
    total_steps: number;
    stage: string;
    detail: string;
    actions_so_far: number;
}

export async function getGenerationProgress(brandId: string): Promise<GenerationProgress> {
    return api<GenerationProgress>(`/intelligence/actions/${brandId}/progress`);
}

export function streamGenerationProgress(
    brandId: string,
    onProgress: (p: GenerationProgress) => void,
    onDone: () => void,
): () => void {
    const token = getToken();
    const url = `${API_BASE}/intelligence/actions/${brandId}/progress/stream`;
    const controller = new AbortController();

    (async () => {
        try {
            const resp = await fetch(url, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                signal: controller.signal,
            });
            if (!resp.ok || !resp.body) { onDone(); return; }
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop() || "";
                for (const line of lines) {
                    const match = line.match(/^data:\s*(.*)/);
                    if (match) {
                        try {
                            const data = JSON.parse(match[1]) as GenerationProgress;
                            onProgress(data);
                            if (data.status === "completed" || data.status === "failed" || data.status === "timeout") {
                                onDone();
                                return;
                            }
                        } catch { /* ignore parse errors */ }
                    }
                }
            }
        } catch {
            /* aborted or network error */
        }
        onDone();
    })();

    return () => controller.abort();
}

export async function getActions(brandId: string): Promise<ActionsResponse> {
    return api<ActionsResponse>(`/intelligence/actions/${brandId}`);
}

export async function updateActionStatus(brandId: string, actionId: string, status: string): Promise<ActionItem> {
    return api<ActionItem>(`/intelligence/actions/${brandId}/${actionId}`, {
        method: "PATCH",
        body: { status },
    });
}

export async function verifyAction(brandId: string, actionId: string): Promise<ActionItem> {
    return api<ActionItem>(`/intelligence/actions/${brandId}/${actionId}/verify`, {
        method: "POST",
    });
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
