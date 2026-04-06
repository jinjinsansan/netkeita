import type { RaceSummary, RaceMatrix } from "./types";

const API_URL = "https://bot.dlogicai.in/nk";

// --- Auth helpers ---

const TOKEN_KEY = "nk_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export async function getLineLoginUrl(): Promise<{ url: string; state: string }> {
  const res = await fetch(`${API_URL}/api/auth/line-url`);
  return res.json();
}

export async function lineCallback(code: string, state: string): Promise<{
  success: boolean;
  token?: string;
  user?: { display_name: string; picture_url: string };
  error?: string;
}> {
  const res = await fetch(`${API_URL}/api/auth/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state }),
  });
  return res.json();
}

export async function getMe(): Promise<{
  authenticated: boolean;
  user?: { display_name: string; picture_url: string; is_admin?: boolean };
}> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/api/auth/me`, { headers });
  return res.json();
}

export async function fetchDates(): Promise<string[]> {
  if (!API_URL) return [];
  try {
    const res = await fetch(`${API_URL}/api/dates`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.dates || [];
  } catch {
    return [];
  }
}

export async function fetchRaces(date: string): Promise<{
  date: string;
  venues: { venue: string; races: RaceSummary[] }[];
}> {
  if (!API_URL) return { date, venues: [] };

  try {
    const res = await fetch(`${API_URL}/api/races?date=${date}`, { cache: "no-store" });
    if (!res.ok) return { date, venues: [] };
    const data = await res.json();
    const races: RaceSummary[] = data.races || [];

    const venueMap: Record<string, RaceSummary[]> = {};
    for (const r of races) {
      const v = r.venue || "不明";
      (venueMap[v] ||= []).push(r);
    }
    return {
      date: data.date || date,
      venues: Object.entries(venueMap).map(([venue, races]) => ({ venue, races })),
    };
  } catch {
    return { date, venues: [] };
  }
}

export interface InternetPrediction {
  race_name: string;
  youtube?: {
    source_count: string;
    horses: { rank: number; mark: string; name: string; support_rate: number }[];
  };
  keiba_site?: {
    source_count: string;
    horses: { rank: number; mark: string; name: string; support_rate: number }[];
  };
  highlights?: string[];
}

export async function fetchInternetPredictions(raceName: string): Promise<InternetPrediction | null> {
  if (!API_URL) return null;
  try {
    const res = await fetch(`${API_URL}/api/internet-predictions/${encodeURIComponent(raceName)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface HorseDetail {
  horse_number: number;
  horse_name: string;
  is_local?: boolean;
  stable_comment: {
    horse_name?: string;
    mark?: string;
    status?: string;
    trainer?: string;
    comment?: string;
  };
  recent_runs: {
    date: string;
    venue: string;
    distance: string;
    finish: number;
    jockey: string;
    odds: number;
    race_name?: string;
    class_name?: string;
    time?: string;
    agari?: string;
    popularity?: number;
    corner?: string;
    weight?: string;
    track_condition?: string;
    headcount?: number;
  }[];
  course_stats?: Record<string, {
    record: string;
    win_rate: string;
    place_rate: string;
  }>;
  bloodline: {
    sire?: string;
    broodmare_sire?: string;
    sire_performance?: {
      total_races: number;
      place_rate: number;
      by_condition?: { condition: string; races: number; place: number; place_rate: number }[];
    };
    broodmare_performance?: {
      total_races: number;
      place_rate: number;
    };
    sire_course_stats?: {
      course_key: string;
      total_runs: number;
      wins: number;
      place_count: number;
      win_rate: number;
      place_rate: number;
    };
  };
}

export async function fetchHorseDetail(raceId: string, horseNumber: number): Promise<HorseDetail | null> {
  if (!API_URL) return null;
  try {
    const res = await fetch(
      `${API_URL}/api/horse-detail/${encodeURIComponent(raceId)}/${horseNumber}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// --- Minna-no-Yosou (みんなの予想) ---

export interface VoteResult {
  horse_number: number;
  horse_name: string;
  post: number;
  jockey: string;
  votes: number;
  rate: number;
}

export interface VoteResults {
  race_id: string;
  total_votes: number;
  results: VoteResult[];
  my_vote: number | null;
}

export interface CharacterPrediction {
  id: string;
  name: string;
  description: string;
  emoji: string;
  marks: Record<string, string>;
}

export interface CharacterPredictionsResponse {
  race_id: string;
  predictions: CharacterPrediction[];
}

export async function fetchVoteResults(raceId: string): Promise<VoteResults | null> {
  if (!API_URL) return null;
  try {
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(
      `${API_URL}/api/votes/${encodeURIComponent(raceId)}/results`,
      { cache: "no-store", headers }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchCharacterPredictions(raceId: string): Promise<CharacterPrediction[]> {
  if (!API_URL) return [];
  try {
    const res = await fetch(
      `${API_URL}/api/votes/${encodeURIComponent(raceId)}/predictions`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data: CharacterPredictionsResponse = await res.json();
    return data.predictions || [];
  } catch {
    return [];
  }
}

export async function submitVote(
  raceId: string,
  horseNumber: number
): Promise<{ success: boolean; error?: string; oddsAtVote?: number }> {
  if (!API_URL) return { success: false, error: "API unavailable" };
  try {
    const token = getToken();
    if (!token) return { success: false, error: "ログインが必要です" };
    const res = await fetch(`${API_URL}/api/votes/${encodeURIComponent(raceId)}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ horse_number: horseNumber }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return { success: false, error: data.detail || "投票に失敗しました" };
    }
    const data = await res.json().catch(() => ({}));
    return { success: true, oddsAtVote: typeof data.odds_at_vote === "number" ? data.odds_at_vote : undefined };
  } catch {
    return { success: false, error: "通信エラーが発生しました" };
  }
}

export type VoteResultStatus =
  | "pending"
  | "hit"
  | "miss"
  | "hit_no_payout"
  | "cancelled";

export interface VoteHistoryEntry {
  race_id: string;
  date: string;
  venue: string;
  race_number: string;
  race_name: string;
  horse_number: number;
  horse_name: string;
  odds: number;
  result: VoteResultStatus;
  payout: number;
}

export interface VoteHistory {
  history: VoteHistoryEntry[];
  total_races: number;
  hits: number;
  hit_rate: number;
  roi: number;
  total_bet: number;
  total_return: number;
  finalized_count: number;
  pending_count: number;
  cancelled_count: number;
}

export async function fetchMyVoteHistory(): Promise<VoteHistory | null> {
  if (!API_URL) return null;
  try {
    const token = getToken();
    if (!token) return null;
    const res = await fetch(`${API_URL}/api/votes/my-history`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchMatrix(raceId: string): Promise<RaceMatrix | null> {
  if (!API_URL) return null;

  try {
    const res = await fetch(`${API_URL}/api/race/${encodeURIComponent(raceId)}/matrix`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// --- Article posting (note-style) ---

export interface ArticleSummary {
  slug: string;
  title: string;
  description: string;
  thumbnail_url: string;
  author: string;
  status: "published" | "draft";
  created_at: string;
  updated_at: string;
}

export interface Article extends ArticleSummary {
  body: string;
  /** Estimated reading time in minutes (backend-computed). */
  reading_time_minutes?: number;
  /**
   * Admin's LINE user id.
   * Only returned by the backend when the caller is the admin themselves;
   * public readers never see this field (server-side `public_view`).
   */
  author_id?: string;
}

export interface ArticleInput {
  title: string;
  description?: string;
  body: string;
  thumbnail_url?: string;
  status: "published" | "draft";
  slug?: string;
  /**
   * Optimistic-lock sentinel. Send the article's `updated_at` value that
   * was shown to the editor; the server returns 409 if it has changed.
   */
  expected_updated_at?: string;
}

export interface ArticleListResponse {
  articles: ArticleSummary[];
  count: number;
  total_count: number;
  has_more: boolean;
  offset: number;
  limit: number;
}

export type ArticleMutationResult =
  | { success: true; article: Article }
  | { success: false; error: string; conflict?: boolean };

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Low-level fetch that also returns the raw list pagination fields. */
export async function fetchArticlePage(
  opts: { includeDrafts?: boolean; limit?: number; offset?: number } = {}
): Promise<ArticleListResponse> {
  const empty: ArticleListResponse = {
    articles: [],
    count: 0,
    total_count: 0,
    has_more: false,
    offset: 0,
    limit: opts.limit ?? 50,
  };
  if (!API_URL) return empty;
  try {
    const params = new URLSearchParams();
    if (opts.includeDrafts) params.set("include_drafts", "true");
    if (opts.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts.offset !== undefined) params.set("offset", String(opts.offset));
    const qs = params.toString();
    const url = `${API_URL}/api/articles${qs ? `?${qs}` : ""}`;
    const res = await fetch(url, { cache: "no-store", headers: { ...authHeaders() } });
    if (!res.ok) return empty;
    const data = (await res.json()) as Partial<ArticleListResponse>;
    return {
      articles: data.articles || [],
      count: data.count ?? 0,
      total_count: data.total_count ?? 0,
      has_more: !!data.has_more,
      offset: data.offset ?? opts.offset ?? 0,
      limit: data.limit ?? opts.limit ?? 50,
    };
  } catch {
    return empty;
  }
}

/** Back-compat shortcut that returns only the article list. */
export async function fetchArticles(
  includeDrafts = false
): Promise<ArticleSummary[]> {
  const page = await fetchArticlePage({ includeDrafts });
  return page.articles;
}

export async function fetchArticle(slug: string): Promise<Article | null> {
  if (!API_URL) return null;
  try {
    const res = await fetch(
      `${API_URL}/api/articles/${encodeURIComponent(slug)}`,
      { cache: "no-store", headers: { ...authHeaders() } }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function createArticle(
  input: ArticleInput
): Promise<ArticleMutationResult> {
  if (!API_URL) return { success: false, error: "API unavailable" };
  try {
    const res = await fetch(`${API_URL}/api/articles`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(input),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { success: false, error: data.detail || "作成に失敗しました" };
    }
    return { success: true, article: data };
  } catch {
    return { success: false, error: "通信エラーが発生しました" };
  }
}

export async function updateArticle(
  slug: string,
  input: Partial<ArticleInput>
): Promise<ArticleMutationResult> {
  if (!API_URL) return { success: false, error: "API unavailable" };
  try {
    const res = await fetch(
      `${API_URL}/api/articles/${encodeURIComponent(slug)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(input),
      }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        success: false,
        error: data.detail || "更新に失敗しました",
        conflict: res.status === 409,
      };
    }
    return { success: true, article: data };
  } catch {
    return { success: false, error: "通信エラーが発生しました" };
  }
}

export async function uploadArticleImage(
  file: File
): Promise<{ success: boolean; url?: string; error?: string }> {
  if (!API_URL) return { success: false, error: "API unavailable" };
  // Simple client-side guard rails so we don't even send obviously bad files.
  if (file.size > 5 * 1024 * 1024) {
    return { success: false, error: "ファイルサイズが大きすぎます (最大 5MB)" };
  }
  if (!/^image\/(jpeg|jpg|png|webp|gif)$/i.test(file.type)) {
    return {
      success: false,
      error: "画像形式が未対応です (JPEG / PNG / WebP / GIF)",
    };
  }
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/articles/upload-image`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        success: false,
        error: data.detail || "画像アップロードに失敗しました",
      };
    }
    return { success: true, url: data.url };
  } catch {
    return { success: false, error: "通信エラーが発生しました" };
  }
}

export async function deleteArticle(
  slug: string
): Promise<{ success: boolean; error?: string }> {
  if (!API_URL) return { success: false, error: "API unavailable" };
  try {
    const res = await fetch(
      `${API_URL}/api/articles/${encodeURIComponent(slug)}`,
      { method: "DELETE", headers: { ...authHeaders() } }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return { success: false, error: data.detail || "削除に失敗しました" };
    }
    return { success: true };
  } catch {
    return { success: false, error: "通信エラーが発生しました" };
  }
}
