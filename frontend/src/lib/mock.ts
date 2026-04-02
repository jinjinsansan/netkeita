import type { Grade, HorseRank, RaceSummary, RaceMatrix } from "./types";
import sampleData from "./sample_data.json";

function g(rank: number, total: number): Grade {
  if (rank === 1) return "S";
  const pct = rank / total;
  if (pct <= 0.25) return "A";
  if (pct <= 0.5) return "B";
  if (pct <= 0.75) return "C";
  return "D";
}

// Generate pseudo-scores from horse data for visual development
function generateScores(entry: { horse_number: number; post: number; weight: number }, total: number, seed: number): HorseRank["scores"] {
  // Deterministic pseudo-random based on horse_number + seed
  const hash = (n: number) => ((n * 2654435761) >>> 0) % 1000 / 10;
  return {
    total: hash(entry.horse_number * 7 + seed),
    speed: hash(entry.horse_number * 13 + seed + 1),
    flow: hash(entry.horse_number * 17 + seed + 2),
    jockey: hash(entry.horse_number * 23 + seed + 3),
    bloodline: hash(entry.horse_number * 29 + seed + 4),
    recent: hash(entry.horse_number * 31 + seed + 5),
    track: hash(entry.horse_number * 37 + seed + 6),
    ev: hash(entry.horse_number * 41 + seed + 7),
  };
}

function buildMatrix(race: (typeof sampleData.races)[0]): RaceMatrix {
  const total = race.entries.length;
  const seed = race.race_number * 100 + race.venue.charCodeAt(0);

  const horses: HorseRank[] = race.entries.map((e) => {
    const scores = generateScores(e, total, seed);
    return {
      horse_number: e.horse_number,
      horse_name: e.horse_name,
      jockey: e.jockey,
      post: e.post,
      scores,
      ranks: {} as HorseRank["ranks"],
    };
  });

  // Assign grades per category
  const keys: (keyof HorseRank["scores"])[] = ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"];
  for (const key of keys) {
    const sorted = [...horses].sort((a, b) => b.scores[key] - a.scores[key]);
    sorted.forEach((h, i) => {
      h.ranks[key] = g(i + 1, total);
    });
  }

  return {
    race_id: race.race_id,
    race_name: race.race_name,
    venue: race.venue,
    distance: race.distance,
    race_number: race.race_number,
    track_condition: race.track_condition || "良",
    horses,
  };
}

// Build race list grouped by venue
interface VenueGroup {
  date: string;
  venue: string;
  races: RaceSummary[];
}

export const MOCK_RACES: VenueGroup[] = (() => {
  const venueMap: Record<string, RaceSummary[]> = {};
  for (const r of sampleData.races) {
    const v = r.venue;
    if (!venueMap[v]) venueMap[v] = [];
    venueMap[v].push({
      race_id: r.race_id,
      race_number: r.race_number,
      race_name: r.race_name,
      venue: r.venue,
      distance: r.distance,
      headcount: r.headcount,
      start_time: r.start_time,
      track_condition: r.track_condition,
    });
  }
  return Object.entries(venueMap).map(([venue, races]) => ({
    date: sampleData.date,
    venue,
    races: races.sort((a, b) => a.race_number - b.race_number),
  }));
})();

// Pre-build matrix for each race
const _matrixCache: Record<string, RaceMatrix> = {};
for (const race of sampleData.races) {
  _matrixCache[race.race_id] = buildMatrix(race);
}

export function getMockMatrix(raceId: string): RaceMatrix | null {
  return _matrixCache[raceId] || null;
}

// Keep MOCK_MATRIX for backward compat (first race)
export const MOCK_MATRIX: RaceMatrix = Object.values(_matrixCache)[0];
