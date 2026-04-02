import type { RaceSummary, RaceMatrix } from "./types";
import { MOCK_RACES, getMockMatrix } from "./mock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const USE_MOCK = !API_URL || API_URL === "mock";

export async function fetchRaces(date: string): Promise<{
  date: string;
  venues: { venue: string; races: RaceSummary[] }[];
}> {
  if (USE_MOCK) {
    // Filter by date (mock data has single date)
    const groups = MOCK_RACES.filter((r) => r.date === date || date === "");
    return {
      date: date || MOCK_RACES[0]?.date || "",
      venues: groups.map((g) => ({ venue: g.venue, races: g.races })),
    };
  }

  const res = await fetch(`${API_URL}/api/races?date=${date}`, { next: { revalidate: 300 } });
  if (!res.ok) return { date, venues: [] };
  const data = await res.json();
  const races: RaceSummary[] = data.races || [];

  const venueMap: Record<string, RaceSummary[]> = {};
  for (const r of races) {
    const v = r.venue || "不明";
    (venueMap[v] ||= []).push(r);
  }
  return {
    date,
    venues: Object.entries(venueMap).map(([venue, races]) => ({ venue, races })),
  };
}

export async function fetchMatrix(raceId: string): Promise<RaceMatrix | null> {
  if (USE_MOCK) {
    return getMockMatrix(raceId);
  }

  const res = await fetch(`${API_URL}/api/race/${encodeURIComponent(raceId)}/matrix`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) return null;
  return res.json();
}

export function getAvailableDates(): string[] {
  if (USE_MOCK) {
    return [...new Set(MOCK_RACES.map((r) => r.date))];
  }
  return [];
}
