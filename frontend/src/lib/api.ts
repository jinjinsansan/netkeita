import type { RaceSummary, RaceMatrix } from "./types";
import { MOCK_RACES, MOCK_MATRIX } from "./mock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const USE_MOCK = !API_URL || API_URL === "mock";

export async function fetchRaces(date: string): Promise<{ date: string; venues: { venue: string; races: RaceSummary[] }[] }> {
  if (USE_MOCK) {
    const groups = MOCK_RACES.filter((r) => r.date === date);
    return {
      date,
      venues: groups.map((g) => ({ venue: g.venue, races: g.races })),
    };
  }

  const res = await fetch(`${API_URL}/api/races?date=${date}`, { next: { revalidate: 300 } });
  if (!res.ok) return { date, venues: [] };
  const data = await res.json();
  const races: RaceSummary[] = data.races || [];

  // Group by venue
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
    return MOCK_MATRIX;
  }

  const res = await fetch(`${API_URL}/api/race/${encodeURIComponent(raceId)}/matrix`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) return null;
  return res.json();
}
