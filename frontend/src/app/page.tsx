"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import RankBadge from "@/components/RankBadge";
import type { Grade, RaceSummary } from "@/lib/types";
import { fetchDates, fetchRaces, getLineLoginUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

/* ── Venue tab ordering ─── */
const JRA_VENUE_ORDER = ["中山", "阪神", "中京", "東京", "京都", "小倉", "新潟", "札幌", "函館", "福島"];
const NAR_VENUE_ORDER = ["大井", "川崎", "船橋", "浦和", "園田", "姫路", "名古屋", "笠松", "金沢", "高知", "佐賀", "盛岡", "水沢", "門別", "帯広"];
const VENUE_ORDER = [...JRA_VENUE_ORDER, ...NAR_VENUE_ORDER];
function venueSort(a: string, b: string) {
  return (VENUE_ORDER.indexOf(a) === -1 ? 99 : VENUE_ORDER.indexOf(a)) - (VENUE_ORDER.indexOf(b) === -1 ? 99 : VENUE_ORDER.indexOf(b));
}
const NAR_VENUE_SET = new Set(NAR_VENUE_ORDER);
function isNarVenue(venue: string): boolean {
  return NAR_VENUE_SET.has(venue);
}

/* ── Demo data for Hero matrix preview ── */
const DEMO_HORSES: {
  post: number; number: number; name: string; jockey: string;
  ranks: Record<string, Grade>;
}[] = [
  { post: 5, number: 7, name: "ショウナンバルディ", jockey: "C.ルメール", ranks: { total: "S", speed: "A", flow: "S", jockey: "A", bloodline: "S", recent: "A", track: "B", ev: "S" } },
  { post: 3, number: 4, name: "タイセイドリーマー", jockey: "川田将雅", ranks: { total: "A", speed: "S", flow: "A", jockey: "S", bloodline: "A", recent: "B", track: "A", ev: "A" } },
  { post: 7, number: 12, name: "メイショウハリオ", jockey: "武豊", ranks: { total: "A", speed: "A", flow: "B", jockey: "A", bloodline: "B", recent: "S", track: "A", ev: "B" } },
];

const WAKU_BG: Record<number, string> = {
  1: "bg-white text-[#333] border border-[#ccc]",
  2: "bg-black text-white",
  3: "bg-[#ee0000] text-white",
  4: "bg-[#0066ff] text-white",
  5: "bg-[#ffcc00] text-[#333]",
  6: "bg-[#00aa00] text-white",
  7: "bg-[#ff8800] text-white",
  8: "bg-[#ff66cc] text-[#333]",
};

const RANK_COLS = [
  { key: "total", label: "総合" }, { key: "speed", label: "速度" },
  { key: "flow", label: "展開" }, { key: "jockey", label: "騎手" },
  { key: "bloodline", label: "血統" }, { key: "recent", label: "近走" },
  { key: "track", label: "馬場" }, { key: "ev", label: "EV" },
];

const FEATURES = [
  { title: "8項目のランク指数", desc: "総合・スピード・展開・騎手・血統・近走・馬場・期待値をS〜Dで一目把握。" },
  { title: "JRA・地方競馬対応", desc: "JRA全レースに加え、大井・川崎・高知・佐賀など全国の地方競馬もカバー。" },
  { title: "独自の複合AI分析", desc: "複数の独立したAIが異なる角度から分析し、多角的な指数を生成。" },
  { title: "モバイルファースト", desc: "スマホで直感的に操作。横スクロールで8項目を一覧比較。" },
  { title: "期待値（EV）表示", desc: "AI予測勝率とオッズから算出。回収率を意識した馬券戦略をサポート。" },
  { title: "完全無料", desc: "LINEログインだけですべての機能が使えます。課金要素なし。" },
];

/* ── Format date ─── */
function formatDate(d: string): string {
  const dt = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`);
  const days = ["日", "月", "火", "水", "木", "金", "土"];
  return `${dt.getMonth() + 1}/${dt.getDate()}(${days[dt.getDay()]})`;
}

interface VenueGroup {
  venue: string;
  races: RaceSummary[];
}

interface DateData {
  date: string;
  label: string;
  venues: VenueGroup[];
}

export default function LandingPage() {
  const { loading: authLoading, authenticated, user } = useAuth();
  const [allDates, setAllDates] = useState<DateData[]>([]);
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [selectedVenue, setSelectedVenue] = useState("");
  const [loading, setLoading] = useState(true);

  const handleLineLogin = async () => {
    try {
      const { url } = await getLineLoginUrl();
      if (url) window.location.href = url;
    } catch { /* ignore */ }
  };

  useEffect(() => {
    (async () => {
      try {
        const dates = await fetchDates();
        // Take the latest weekend pair (up to 2 dates)
        const recentDates = dates.slice(0, 2);
        if (recentDates.length === 0) {
          setLoading(false);
          return;
        }
        const results: DateData[] = await Promise.all(
          recentDates.map(async (d) => {
            const result = await fetchRaces(d);
            const sorted = result.venues.sort((a, b) => venueSort(a.venue, b.venue));
            return { date: d, label: formatDate(d), venues: sorted };
          })
        );
        // Sort by date ascending (Saturday first, Sunday second)
        results.sort((a, b) => a.date.localeCompare(b.date));
        setAllDates(results);
        setSelectedDateIdx(0);
        if (results[0].venues.length > 0) {
          setSelectedVenue(results[0].venues[0].venue);
        }
      } catch (e) {
        console.error("Failed to fetch races:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const currentDateData = allDates[selectedDateIdx];
  const venues = currentDateData?.venues || [];
  const currentRaces = venues.find((v) => v.venue === selectedVenue)?.races || [];

  function handleDateChange(idx: number) {
    setSelectedDateIdx(idx);
    const v = allDates[idx]?.venues || [];
    if (v.length > 0) {
      setSelectedVenue(v[0].venue);
    }
  }

  return (
    <div className="bg-white">
      {/* ── Hero Section ─────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-[#f8faf8] to-white">
        <div className="max-w-[960px] mx-auto px-5 pt-14 pb-10 md:pt-20 md:pb-14 text-center">
          <div className="inline-flex items-center gap-1.5 bg-[#e8f5e9] text-[#1f7a1f] text-xs font-bold px-4 py-1.5 rounded-full mb-6">
            <span className="w-2 h-2 bg-[#1f7a1f] rounded-full animate-pulse shrink-0" />
            完全無料 · LINEログインですぐ使える
          </div>

          <h1 className="text-[28px] md:text-[42px] font-black text-[#111] leading-[1.3] mb-5">
            JRA・地方競馬の<br className="md:hidden" />
            <span className="text-[#1f7a1f]">8つの指数</span>で<br className="md:hidden" />
            可視化する
          </h1>
          <p className="text-[14px] sm:text-[15px] md:text-lg text-[#444] max-w-lg mx-auto mb-8 md:mb-10 leading-relaxed">
            総合・スピード・展開・騎手・血統・近走・馬場・期待値。<br className="hidden md:block" />
            独自のAI分析が生成するランク指数で、全馬を一目で比較。
          </p>

          {/* CTA */}
          <div className="flex flex-col items-center gap-3 mb-10 min-h-[72px]">
            {authLoading ? null : authenticated ? (
              <>
                <a
                  href="#races"
                  className="flex items-center gap-2.5 bg-[#1f7a1f] hover:bg-[#16611a] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all w-full max-w-[320px] justify-center"
                >
                  レース一覧を見る
                </a>
                <span className="text-xs text-[#999]">{user?.display_name}さん、ようこそ</span>
              </>
            ) : (
              <>
                <button
                  onClick={handleLineLogin}
                  className="flex items-center gap-2.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all w-full max-w-[320px] justify-center"
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
                  LINEでログインして見る
                </button>
                <span className="text-xs text-[#999]">登録不要 · 30秒で完了</span>
              </>
            )}
          </div>

          {/* Mini matrix preview */}
          <div className="max-w-[500px] mx-auto overflow-x-auto border border-[#bbb] rounded bg-white shadow-md">
            <table className="nk-table">
              <thead>
                <tr>
                  <th className="w-9">枠</th><th className="w-9">番</th>
                  <th className="min-w-[100px] text-left">馬名</th>
                  {RANK_COLS.map((c) => <th key={c.key} className="w-[36px]">{c.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {DEMO_HORSES.map((h) => (
                  <tr key={h.number}>
                    <td className="text-center"><span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${WAKU_BG[h.post]||""}`}>{h.post}</span></td>
                    <td className="text-center font-bold text-sm">{h.number}</td>
                    <td className="text-left text-sm font-medium whitespace-nowrap">{h.name}</td>
                    {RANK_COLS.map((c) => <td key={c.key} className="text-center"><RankBadge grade={h.ranks[c.key]} /></td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[#aaa] mt-2">↑ サンプル表示。ログインすると全馬・全レースが閲覧できます</p>
        </div>
      </section>

      {/* ── Real Race List Section ────────────────────── */}
      <section id="races" className="bg-[#f0f0f0] py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-5">
            <h2 className="text-xl md:text-2xl font-black text-[#111] mb-1">
              今週のレース
            </h2>
            {loading ? (
              <p className="text-sm text-[#888]">読み込み中...</p>
            ) : allDates.length > 0 ? (
              <p className="text-sm text-[#888]">レースをタップしてランク指数をチェック</p>
            ) : (
              <p className="text-sm text-[#888]">現在表示できるレースデータがありません</p>
            )}
          </div>

          {allDates.length > 0 && (
            <>
              {/* Date tabs - only show when there are multiple dates */}
              {allDates.length > 1 && (
                <div className="flex items-center gap-2 mb-4 justify-center">
                  {allDates.map((d, i) => (
                    <button
                      key={d.date}
                      onClick={() => handleDateChange(i)}
                      className={`px-4 sm:px-5 py-2 text-sm font-bold rounded-lg border transition ${
                        selectedDateIdx === i
                          ? "bg-[#1f7a1f] text-white border-[#1f7a1f]"
                          : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
                      }`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              )}
              {allDates.length === 1 && (
                <div className="text-center mb-4">
                  <span className="inline-block px-4 py-1.5 text-sm font-bold text-[#1f7a1f] bg-[#e8f5e9] rounded-full">
                    {allDates[0].label}
                  </span>
                </div>
              )}

              {/* Venue tabs — split into JRA and NAR groups */}
              {(() => {
                const jraVenues = venues.filter((v) => !isNarVenue(v.venue));
                const narVenues = venues.filter((v) => isNarVenue(v.venue));
                return (
                  <div className="mb-4 space-y-2">
                    {jraVenues.length > 0 && (
                      <div className="flex items-center gap-0 justify-center flex-wrap">
                        <span className="text-[11px] font-bold text-[#1f7a1f] mr-2 px-2 py-1 bg-[#e8f5e9] rounded">JRA</span>
                        {jraVenues.map((v) => (
                          <button
                            key={v.venue}
                            onClick={() => setSelectedVenue(v.venue)}
                            className={`px-4 sm:px-5 py-2 text-sm font-bold border transition ${
                              selectedVenue === v.venue
                                ? "bg-[#1f7a1f] text-white border-[#1f7a1f]"
                                : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
                            }`}
                          >
                            {v.venue}
                          </button>
                        ))}
                      </div>
                    )}
                    {narVenues.length > 0 && (
                      <div className="flex items-center gap-0 justify-center flex-wrap">
                        <span className="text-[11px] font-bold text-[#7b1fa2] mr-2 px-2 py-1 bg-[#f3e5f5] rounded">地方</span>
                        {narVenues.map((v) => (
                          <button
                            key={v.venue}
                            onClick={() => setSelectedVenue(v.venue)}
                            className={`px-4 sm:px-5 py-2 text-sm font-bold border transition ${
                              selectedVenue === v.venue
                                ? "bg-[#7b1fa2] text-white border-[#7b1fa2]"
                                : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
                            }`}
                          >
                            {v.venue}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Race number tiles */}
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 mb-5 max-w-[540px] mx-auto">
                {currentRaces.map((race) => {
                  const nar = race.is_local || isNarVenue(race.venue);
                  return (
                    <Link
                      key={race.race_id}
                      href={`/race/${encodeURIComponent(race.race_id)}`}
                      className={`flex flex-col items-center justify-center h-[58px] border rounded-lg bg-white transition text-center shadow-sm ${
                        nar
                          ? "border-[#c6c9d3] hover:bg-[#faf5fc] hover:border-[#7b1fa2]"
                          : "border-[#c6c9d3] hover:bg-[#f0f7f0] hover:border-[#1f7a1f]"
                      }`}
                    >
                      <span className={`text-base font-bold ${nar ? "text-[#7b1fa2]" : "text-[#1f7a1f]"}`}>{race.race_number}R</span>
                      <span className="text-[10px] text-[#888] truncate w-full px-1 leading-tight">
                        {race.race_name}
                      </span>
                    </Link>
                  );
                })}
              </div>

              {/* Race list table */}
              <div className="bg-white border border-[#c6c9d3] rounded-lg overflow-x-auto shadow-sm">
                <table className="nk-table">
                  <thead>
                    <tr>
                      <th className="w-12">R</th>
                      <th>レース名</th>
                      <th className="w-24">距離</th>
                      <th className="w-14">頭数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentRaces.map((race) => {
                      const nar = race.is_local || isNarVenue(race.venue);
                      return (
                        <tr key={race.race_id}>
                          <td className={`text-center font-bold text-base ${nar ? "text-[#7b1fa2]" : "text-[#1f7a1f]"}`}>{race.race_number}</td>
                          <td>
                            <Link
                              href={`/race/${encodeURIComponent(race.race_id)}`}
                              className="text-[#1565C0] hover:underline font-bold text-sm inline-flex items-center gap-1.5"
                            >
                              {nar && (
                                <span className="text-[9px] font-bold text-[#7b1fa2] bg-[#f3e5f5] px-1.5 py-0.5 rounded">地方</span>
                              )}
                              {race.race_name}
                            </Link>
                          </td>
                          <td className="text-center text-sm text-[#555]">{race.distance}</td>
                          <td className="text-center text-sm">{race.headcount}頭</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {!authLoading && !authenticated && (
                <div className="mt-4 text-center">
                  <p className="text-sm text-[#666] mb-3">
                    レースをタップするとランク指数が確認できます（要ログイン）
                  </p>
                  <button
                    onClick={handleLineLogin}
                    className="inline-flex items-center gap-2 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-sm px-6 py-3 rounded-xl shadow-md transition-all"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
                    LINEでログインして全レースを見る
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      {/* ── Features Section ─────────────────────────── */}
      <section id="features" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#111] mb-2">
              netkeita の<span className="text-[#1f7a1f]">特長</span>
            </h2>
            <p className="text-sm md:text-base text-[#666]">予想サイトではなく「データ閲覧サイト」</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="border-l-4 border-l-[#1f7a1f] border border-[#d0d0d0] rounded-lg p-5 bg-white shadow-sm hover:shadow-md transition">
                <h3 className="text-base font-bold text-[#111] mb-1.5">{f.title}</h3>
                <p className="text-sm text-[#555] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 8 Rank Items ─────────────────────────────── */}
      <section className="bg-[#f8faf8] py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#111] mb-2">
              <span className="text-[#1f7a1f]">8項目</span>のランク指数
            </h2>
            <p className="text-sm md:text-base text-[#666]">各項目を出走馬全頭の相対順位でS〜Dにランク付け</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "総合", grade: "S" as Grade, engine: "統合スコア", desc: "全エンジンの総合評価" },
              { label: "スピード", grade: "A" as Grade, engine: "能力指数", desc: "10項目の独自スコア" },
              { label: "展開", grade: "A" as Grade, engine: "展開予測", desc: "脚質・先行力の分析" },
              { label: "騎手", grade: "S" as Grade, engine: "騎手統計", desc: "コース別複勝率" },
              { label: "血統", grade: "B" as Grade, engine: "血統統計", desc: "父・母父のコース適性" },
              { label: "近走", grade: "A" as Grade, engine: "直近5走", desc: "着順平均+トレンド" },
              { label: "馬場", grade: "B" as Grade, engine: "馬場補正", desc: "馬場適性の補正係数" },
              { label: "期待値", grade: "S" as Grade, engine: "EV算出", desc: "予測勝率÷オッズ" },
            ].map((item) => (
              <div key={item.label} className="border border-[#d0d0d0] rounded-lg p-4 bg-white text-center shadow-sm">
                <RankBadge grade={item.grade} />
                <h3 className="text-base font-bold text-[#111] mt-2 mb-1">{item.label}</h3>
                <p className="text-xs text-[#1f7a1f] font-bold mb-1">{item.engine}</p>
                <p className="text-xs text-[#555]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How to Use ───────────────────────────────── */}
      <section id="howto" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#111]">
              使い方は<span className="text-[#1f7a1f]">3ステップ</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { step: "01", title: "LINEでログイン", desc: "お持ちのLINEアカウントでワンタップログイン。登録不要。" },
              { step: "02", title: "レースを選ぶ", desc: "日付・競馬場・R番号で今週のレースをかんたん選択。" },
              { step: "03", title: "ランク指数を見る", desc: "8項目のランクマトリクスで全馬を一覧比較。" },
            ].map((s) => (
              <div key={s.step} className="text-center border border-[#d0d0d0] rounded-lg p-6 bg-white shadow-sm">
                <div className="w-12 h-12 bg-[#163016] text-white rounded-full flex items-center justify-center text-base font-black mx-auto mb-4">{s.step}</div>
                <h3 className="text-base font-bold text-[#111] mb-2">{s.title}</h3>
                <p className="text-sm text-[#555] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────── */}
      <section className="bg-gradient-to-b from-[#f0f7f0] to-[#e8f5e9] py-14 md:py-18">
        <div className="max-w-[960px] mx-auto px-5 text-center">
          {authLoading ? (
            <div className="min-h-[120px]" />
          ) : authenticated ? (
            <>
              <h2 className="text-xl md:text-2xl font-black text-[#111] mb-3">
                レース一覧から<br className="md:hidden" />ランク指数を確認しよう
              </h2>
              <p className="text-sm md:text-base text-[#444] mb-8">
                独自AI分析 × 8つの分析項目 × JRA・地方競馬
              </p>
              <a
                href="#races"
                className="inline-flex items-center gap-2.5 bg-[#1f7a1f] hover:bg-[#16611a] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all"
              >
                レース一覧へ
              </a>
            </>
          ) : (
            <>
              <h2 className="text-xl md:text-2xl font-black text-[#111] mb-3">
                今すぐ、全レースの<br className="md:hidden" />ランク指数を確認しよう
              </h2>
              <p className="text-sm md:text-base text-[#444] mb-8">
                独自AI分析 × 8つの分析項目 × JRA・地方競馬
              </p>
              <button
                onClick={handleLineLogin}
                className="inline-flex items-center gap-2.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
                LINEでログインして始める
              </button>
              <p className="text-xs text-[#999] mt-4">完全無料 · 登録不要 · すぐ使える</p>
            </>
          )}
        </div>
      </section>

      {/* Admin-only floating action button for quick article authoring.
          Hidden for non-admins and logged-out users via the is_admin flag. */}
      {user?.is_admin && (
        <Link
          href="/articles/new"
          aria-label="記事を書く"
          className="fixed bottom-5 right-5 md:bottom-8 md:right-8 z-50 inline-flex items-center gap-2 bg-[#1f7a1f] hover:bg-[#16611a] text-white font-bold text-sm px-5 py-3 rounded-full shadow-xl hover:shadow-2xl transition-all"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          記事を書く
        </Link>
      )}
    </div>
  );
}
