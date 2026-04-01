import type { Grade, HorseRank, RaceSummary, RaceMatrix } from "./types";

function g(rank: number, total: number): Grade {
  if (rank === 1) return "S";
  const pct = rank / total;
  if (pct <= 0.25) return "A";
  if (pct <= 0.5) return "B";
  if (pct <= 0.75) return "C";
  return "D";
}

const T = 16; // total horses

function mkHorse(
  num: number,
  name: string,
  jockey: string,
  post: number,
  ranks: [number, number, number, number, number, number, number, number]
): HorseRank {
  const keys = ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"] as const;
  const scores: Record<string, number> = {};
  const grades: Record<string, Grade> = {};
  keys.forEach((k, i) => {
    scores[k] = (T - ranks[i] + 1) * 10;
    grades[k] = g(ranks[i], T);
  });
  return {
    horse_number: num,
    horse_name: name,
    jockey,
    post,
    scores: scores as HorseRank["scores"],
    ranks: grades as HorseRank["ranks"],
  };
}

export const MOCK_MATRIX: RaceMatrix = {
  race_id: "20260405-中山-12",
  race_name: "4歳以上2勝クラス",
  venue: "中山",
  distance: "ダ1200m",
  race_number: 12,
  track_condition: "良",
  horses: [
    mkHorse(6, "ショウナンハクウン", "花田大", 3, [1, 2, 5, 2, 1, 2, 5, 1]),
    mkHorse(11, "タイセイビューマ", "杉原誠", 6, [2, 5, 2, 8, 3, 5, 2, 3]),
    mkHorse(3, "ケンキョ", "横山和", 2, [3, 3, 1, 3, 6, 3, 7, 2]),
    mkHorse(14, "キョウエイカンプ", "秋山稔", 7, [4, 4, 3, 4, 4, 4, 3, 10]),
    mkHorse(15, "サンドプラスト", "プレ", 8, [5, 6, 8, 7, 5, 6, 6, 6]),
    mkHorse(1, "ラヴァグロウ", "ブリ", 1, [6, 11, 4, 6, 7, 7, 4, 4]),
    mkHorse(10, "レッドアレグロ", "ルメール", 5, [7, 7, 7, 1, 2, 1, 1, 13]),
    mkHorse(7, "カワキタマナレア", "海田", 4, [8, 1, 6, 12, 8, 8, 8, 7]),
    mkHorse(12, "モリノレッドスター", "秋山真", 6, [9, 8, 10, 9, 9, 9, 9, 9]),
    mkHorse(13, "ケープアダラス", "宇都", 7, [10, 9, 9, 8, 10, 10, 11, 5]),
    mkHorse(8, "ヘルメース", "黒岩悠", 4, [11, 10, 11, 10, 11, 11, 10, 8]),
    mkHorse(4, "ヴィクトリーロード", "岩田望", 2, [12, 12, 13, 13, 12, 12, 12, 11]),
    mkHorse(2, "ホウオウフロイト", "杉原", 1, [13, 13, 12, 11, 13, 13, 13, 12]),
    mkHorse(16, "アルジェンタージョ", "菅原", 8, [14, 14, 14, 14, 14, 14, 14, 14]),
    mkHorse(9, "ロミオポス", "大野拓", 5, [15, 15, 15, 15, 15, 15, 15, 15]),
    mkHorse(5, "バンブトンプロ", "藤田大", 3, [16, 16, 16, 16, 16, 16, 16, 16]),
  ],
};

export const MOCK_RACES: { date: string; venue: string; races: RaceSummary[] }[] = [
  {
    date: "2026-04-04",
    venue: "中山",
    races: Array.from({ length: 12 }, (_, i) => ({
      race_id: `20260404-中山-${i + 1}`,
      race_number: i + 1,
      race_name: i === 10 ? "ダービー卿チャレンジT" : `${i + 1}R ${i < 4 ? "未勝利" : i < 8 ? "1勝クラス" : "2勝クラス"}`,
      venue: "中山",
      distance: i % 3 === 0 ? "芝1600m" : i % 3 === 1 ? "ダ1200m" : "芝2000m",
      headcount: 14 + (i % 4),
      start_time: `${9 + Math.floor(i / 2)}:${i % 2 === 0 ? "50" : "25"}`,
    })),
  },
  {
    date: "2026-04-04",
    venue: "阪神",
    races: Array.from({ length: 12 }, (_, i) => ({
      race_id: `20260404-阪神-${i + 1}`,
      race_number: i + 1,
      race_name: i === 10 ? "大阪杯" : `${i + 1}R ${i < 4 ? "未勝利" : "1勝クラス"}`,
      venue: "阪神",
      distance: i % 2 === 0 ? "芝2000m" : "ダ1400m",
      headcount: 12 + (i % 5),
      start_time: `${9 + Math.floor(i / 2)}:${i % 2 === 0 ? "45" : "20"}`,
    })),
  },
  {
    date: "2026-04-05",
    venue: "中山",
    races: Array.from({ length: 12 }, (_, i) => ({
      race_id: `20260405-中山-${i + 1}`,
      race_number: i + 1,
      race_name: `${i + 1}R ${i < 4 ? "未勝利" : i < 8 ? "1勝クラス" : "2勝クラス"}`,
      venue: "中山",
      distance: i % 3 === 0 ? "芝1600m" : "ダ1200m",
      headcount: 14 + (i % 3),
      start_time: `${9 + Math.floor(i / 2)}:${i % 2 === 0 ? "50" : "25"}`,
    })),
  },
];
