/**
 * Venue name ↔ short ASCII code mapping.
 *
 * Converts Japanese venue names in race_id strings to compact ASCII codes so
 * that URLs like /race/20260410-%E5%B7%9D%E5%B4%8E-10 become /race/20260410-kws-10.
 *
 * Internal race_id format stays unchanged (YYYYMMDD-<Japanese>-<num>).
 * Only the URL path segment is shortened.
 */

export const VENUE_TO_CODE: Record<string, string> = {
  // JRA
  "東京": "tok",
  "中山": "nky",
  "阪神": "hsn",
  "京都": "kyt",
  "中京": "cky",
  "小倉": "kok",
  "新潟": "ngt",
  "札幌": "spr",
  "函館": "hkd",
  "福島": "fks",
  // NAR
  "大井": "oi",
  "川崎": "kws",
  "船橋": "fnb",
  "浦和": "urw",
  "園田": "snd",
  "姫路": "hmj",
  "名古屋": "ngy",
  "笠松": "ksm",
  "金沢": "knz",
  "高知": "kch",
  "佐賀": "sga",
  "盛岡": "mrk",
  "水沢": "mzs",
  "門別": "mnb",
  "帯広": "obh",
};

export const CODE_TO_VENUE: Record<string, string> = Object.fromEntries(
  Object.entries(VENUE_TO_CODE).map(([venue, code]) => [code, venue])
);

/**
 * Convert internal race_id to a URL-safe path segment.
 * "20260410-川崎-10" → "20260410-kws-10"
 * Falls back to the original string if the venue is not in the mapping.
 */
export function raceIdToPath(raceId: string): string {
  const parts = raceId.split("-");
  if (parts.length < 3) return raceId;
  const code = VENUE_TO_CODE[parts[1]];
  if (!code) return raceId;
  return `${parts[0]}-${code}-${parts.slice(2).join("-")}`;
}

/**
 * Convert a URL path segment back to the internal race_id.
 * "20260410-kws-10" → "20260410-川崎-10"
 * If the second segment is already Japanese (old URL), passes through unchanged.
 */
export function pathToRaceId(path: string): string {
  const parts = path.split("-");
  if (parts.length < 3) return path;
  const venue = CODE_TO_VENUE[parts[1]];
  if (!venue) return path; // already Japanese or unknown code
  return `${parts[0]}-${venue}-${parts.slice(2).join("-")}`;
}
