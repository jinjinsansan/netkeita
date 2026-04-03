export type Grade = "S" | "A" | "B" | "C" | "D";

export interface HorseRank {
  horse_number: number;
  horse_name: string;
  jockey: string;
  post: number; // frame number (1-8)
  odds?: number;
  win_prob?: number;
  place_prob?: number;
  scores: {
    total: number;
    speed: number;
    flow: number;
    jockey: number;
    bloodline: number;
    recent: number;
    track: number;
    ev: number;
  };
  ranks: {
    total: Grade;
    speed: Grade;
    flow: Grade;
    jockey: Grade;
    bloodline: Grade;
    recent: Grade;
    track: Grade;
    ev: Grade;
  };
}

export interface RaceSummary {
  race_id: string;
  race_number: number;
  race_name: string;
  venue: string;
  distance: string;
  headcount: number;
  start_time?: string;
  track_condition?: string;
}

export interface JockeyPostStats {
  horse: string;
  horse_number: number;
  post_zone: string;
  fukusho_rate: number;
  race_count: number;
}

export interface JockeyCourseStats {
  course_key: string;
  total_runs: number;
  wins: number;
  fukusho_count: number;
  win_rate: number;
  fukusho_rate: number;
}

export interface JockeyData {
  jockey_post_stats: Record<string, JockeyPostStats>;
  jockey_course_stats: Record<string, JockeyCourseStats>;
}

export interface RaceMatrix {
  race_id: string;
  race_name: string;
  venue: string;
  distance: string;
  race_number: number;
  track_condition: string;
  horses: HorseRank[];
  jockey_data?: JockeyData;
}

export const RANK_COLUMNS = [
  { key: "total", label: "総合" },
  { key: "speed", label: "速度" },
  { key: "flow", label: "展開" },
  { key: "jockey", label: "騎手" },
  { key: "bloodline", label: "血統" },
  { key: "recent", label: "近走" },
  { key: "track", label: "馬場" },
  { key: "ev", label: "EV" },
] as const;

export type RankKey = (typeof RANK_COLUMNS)[number]["key"];
