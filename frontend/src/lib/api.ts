import type { RaceSummary, RaceMatrix } from "./types";

// API URL — hardcoded to prevent mixed content (Vercel HTTPS → HTTP IP).
// For local dev, change this value or use .env.local override below.
const API_URL = "https://bot.dlogicai.in/nk";

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
  }[];
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
