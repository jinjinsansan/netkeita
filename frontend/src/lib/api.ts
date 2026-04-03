import type { RaceSummary, RaceMatrix } from "./types";

// Production API URL — always use HTTPS domain to avoid mixed content
// Override with NEXT_PUBLIC_API_URL for local dev only (e.g. http://localhost:5002)
const PRODUCTION_API_URL = "https://bot.dlogicai.in/nk";

function resolveApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl) return PRODUCTION_API_URL;
  // Allow localhost/127.0.0.1 for local development
  if (envUrl.includes("localhost") || envUrl.includes("127.0.0.1")) {
    return envUrl;
  }
  // For any non-localhost URL, always use the production HTTPS endpoint
  // to prevent mixed content issues on Vercel (HTTPS site → HTTP API)
  return PRODUCTION_API_URL;
}

const API_URL = resolveApiUrl();

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
