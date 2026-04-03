"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import RankBadge from "@/components/RankBadge";
import type { Grade, RaceSummary } from "@/lib/types";
import { fetchDates, fetchRaces } from "@/lib/api";

const LINE_ADD_URL = "#"; // TODO: LINE Login URL

/* ── Venue tab ordering ─── */
const VENUE_ORDER = ["中山", "阪神", "中京", "東京", "京都", "小倉", "新潟", "札幌", "函館", "福島"];
function venueSort(a: string, b: string) {
  return (VENUE_ORDER.indexOf(a) === -1 ? 99 : VENUE_ORDER.indexOf(a)) - (VENUE_ORDER.indexOf(b) === -1 ? 99 : VENUE_ORDER.indexOf(b));
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
  { icon: "📊", title: "8項目のランク指数", desc: "総合・スピード・展開・騎手・血統・近走・馬場・期待値をS〜Dで一目把握。", highlight: "他にない独自指標" },
  { icon: "🏇", title: "JRA全レース対応", desc: "毎週の土日JRA全36レースを網羅。出走全馬のランクを確認できます。", highlight: "土日全レース" },
  { icon: "🤖", title: "独自の複合AI分析", desc: "4つの独立したAIエンジンが異なる角度から分析し、多角的な指数を生成。", highlight: "4エンジン統合" },
  { icon: "📱", title: "モバイルファースト", desc: "スマホで直感的に操作。横スクロールで8項目を一覧比較。出先でもサクッと確認。", highlight: "レスポンシブ対応" },
  { icon: "🎯", title: "期待値（EV）表示", desc: "AI予測勝率とオッズから算出。回収率を意識した馬券戦略をサポート。", highlight: "回収率重視" },
  { icon: "🆓", title: "完全無料", desc: "LINEログインだけですべての機能が使えます。課金要素なし。", highlight: "課金なし" },
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
  const [allDates, setAllDates] = useState<DateData[]>([]);
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [selectedVenue, setSelectedVenue] = useState("");
  const [loading, setLoading] = useState(true);

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
      <section className="relative overflow-hidden bg-gradient-to-b from-[#f0f4ff] to-white">
        <div className="max-w-[960px] mx-auto px-5 pt-14 pb-10 md:pt-20 md:pb-14 text-center">
          <div className="inline-flex items-center gap-1.5 bg-[#e8eef9] text-[#3251BC] text-xs font-bold px-4 py-1.5 rounded-full mb-6">
            <span className="w-2 h-2 bg-[#3251BC] rounded-full animate-pulse shrink-0" />
            完全無料 · LINEログインですぐ使える
          </div>

          <h1 className="text-[28px] md:text-[42px] font-black text-[#222] leading-[1.3] mb-5">
            JRA全レースを<br className="md:hidden" />
            <span className="text-[#3251BC]">8つの指数</span>で<br className="md:hidden" />
            可視化する
          </h1>
          <p className="text-[15px] md:text-lg text-[#666] max-w-lg mx-auto mb-10 leading-relaxed">
            総合・スピード・展開・騎手・血統・近走・馬場・期待値。<br className="hidden md:block" />
            独自のAI分析が生成するランク指数で、<br className="md:hidden" />全馬を一目で比較。
          </p>

          {/* CTA */}
          <div className="flex flex-col items-center gap-3 mb-10">
            <a
              href={LINE_ADD_URL}
              className="flex items-center gap-2.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all w-full max-w-[320px] justify-center"
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
              LINEでログインして見る
            </a>
            <span className="text-xs text-[#999]">登録不要 · 30秒で完了</span>
          </div>

          {/* Mini matrix preview */}
          <div className="max-w-[500px] mx-auto overflow-x-auto border border-[#c6c9d3] rounded bg-white shadow-sm">
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
      <section className="bg-[#f5f5f5] py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-5">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-1">
              🏇 今週のJRAレース
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
              {/* Date tabs */}
              <div className="flex items-center gap-2 mb-4 justify-center">
                {allDates.map((d, i) => (
                  <button
                    key={d.date}
                    onClick={() => handleDateChange(i)}
                    className={`px-5 py-2 text-sm font-bold rounded-lg border transition ${
                      selectedDateIdx === i
                        ? "bg-[#3251BC] text-white border-[#3251BC]"
                        : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>

              {/* Venue tabs */}
              <div className="flex items-center gap-0 mb-4 justify-center">
                {venues.map((v) => (
                  <button
                    key={v.venue}
                    onClick={() => setSelectedVenue(v.venue)}
                    className={`px-5 py-2 text-sm font-bold border transition ${
                      selectedVenue === v.venue
                        ? "bg-[#3251BC] text-white border-[#3251BC]"
                        : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
                    }`}
                  >
                    {v.venue}
                  </button>
                ))}
              </div>

              {/* Race number tiles */}
              <div className="flex flex-wrap gap-2 mb-5 justify-center">
                {currentRaces.map((race) => (
                  <Link
                    key={race.race_id}
                    href={`/race/${encodeURIComponent(race.race_id)}`}
                    className="flex flex-col items-center justify-center w-[80px] h-[58px] border border-[#c6c9d3] rounded-lg bg-white hover:bg-[#f0f4ff] hover:border-[#3251BC] transition text-center shadow-sm"
                  >
                    <span className="text-base font-bold text-[#3251BC]">{race.race_number}R</span>
                    <span className="text-[11px] text-[#888] truncate max-w-[74px] leading-tight">
                      {race.race_name}
                    </span>
                  </Link>
                ))}
              </div>

              {/* Race list table */}
              <div className="bg-white border border-[#c6c9d3] rounded-lg overflow-hidden">
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
                    {currentRaces.map((race) => (
                      <tr key={race.race_id}>
                        <td className="text-center font-bold text-[#3251BC] text-base">{race.race_number}</td>
                        <td>
                          <Link
                            href={`/race/${encodeURIComponent(race.race_id)}`}
                            className="text-[#1E88E5] hover:underline font-medium text-sm"
                          >
                            {race.race_name}
                          </Link>
                        </td>
                        <td className="text-center text-sm text-[#555]">{race.distance}</td>
                        <td className="text-center text-sm">{race.headcount}頭</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 text-center">
                <p className="text-sm text-[#888] mb-3">
                  レースをタップするとランク指数が確認できます（要ログイン）
                </p>
                <a
                  href={LINE_ADD_URL}
                  className="inline-flex items-center gap-2 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-sm px-6 py-3 rounded-xl shadow-md transition-all"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
                  LINEでログインして全レースを見る
                </a>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ── Features Section ─────────────────────────── */}
      <section id="features" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              netkeita の<span className="text-[#3251BC]">特長</span>
            </h2>
            <p className="text-sm md:text-base text-[#888]">予想サイトではなく「データ閲覧サイト」</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="relative border border-[#e0e0e0] rounded-xl p-5 bg-white hover:border-[#3251BC] hover:shadow-md transition group overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#3251BC] to-[#5a7be0] opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-start gap-3 mb-2">
                  <div className="text-2xl shrink-0 mt-0.5">{f.icon}</div>
                  <div>
                    <h3 className="text-base font-bold text-[#333] mb-0.5">{f.title}</h3>
                    <span className="inline-block text-[10px] font-bold text-[#3251BC] bg-[#eef2fb] px-2 py-0.5 rounded-full">{f.highlight}</span>
                  </div>
                </div>
                <p className="text-sm text-[#666] leading-relaxed mt-2">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 8 Rank Items ─────────────────────────────── */}
      <section className="bg-[#f5f7fc] py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              <span className="text-[#3251BC]">8項目</span>のランク指数
            </h2>
            <p className="text-sm md:text-base text-[#888]">各項目を出走馬全頭の相対順位でS〜Dにランク付け</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "総合", grade: "S" as Grade, engine: "統合スコア", desc: "全エンジンの総合評価", num: "01" },
              { label: "スピード", grade: "A" as Grade, engine: "能力指数", desc: "10項目の独自スコア", num: "02" },
              { label: "展開", grade: "A" as Grade, engine: "展開予測", desc: "脚質・先行力の分析", num: "03" },
              { label: "騎手", grade: "S" as Grade, engine: "騎手統計", desc: "コース別複勝率", num: "04" },
              { label: "血統", grade: "B" as Grade, engine: "血統統計", desc: "父・母父のコース適性", num: "05" },
              { label: "近走", grade: "A" as Grade, engine: "直近5走", desc: "着順平均+トレンド", num: "06" },
              { label: "馬場", grade: "B" as Grade, engine: "馬場補正", desc: "馬場適性の補正係数", num: "07" },
              { label: "期待値", grade: "S" as Grade, engine: "EV算出", desc: "予測勝率÷オッズ", num: "08" },
            ].map((item) => (
              <div key={item.label} className="relative border border-[#e0e0e0] rounded-xl p-4 bg-white text-center hover:shadow-md transition overflow-hidden">
                <span className="absolute top-2 left-3 text-[10px] font-black text-[#ddd]">{item.num}</span>
                <div className="mb-2">
                  <RankBadge grade={item.grade} />
                </div>
                <h3 className="text-base font-bold text-[#333] mb-1">{item.label}</h3>
                <div className="inline-block text-[10px] font-bold text-white bg-[#3251BC] px-2.5 py-0.5 rounded-full mb-1.5">{item.engine}</div>
                <p className="text-xs text-[#888] leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How to Use ───────────────────────────────── */}
      <section id="howto" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222]">
              使い方は<span className="text-[#3251BC]">3ステップ</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 md:gap-0">
            {[
              { step: "01", title: "LINEでログイン", desc: "お持ちのLINEアカウントでワンタップログイン。登録不要、30秒で完了。", icon: "🔑" },
              { step: "02", title: "レースを選ぶ", desc: "日付・競馬場・R番号で今週のレースをタップ選択。直感的なUI。", icon: "🏟" },
              { step: "03", title: "ランク指数を見る", desc: "8項目のランクマトリクスで全馬を一覧比較。馬券戦略に活用。", icon: "📊" },
            ].map((s, i) => (
              <div key={s.step} className="relative text-center px-6 py-8 bg-white border border-[#e0e0e0] first:rounded-t-xl md:first:rounded-l-xl md:first:rounded-tr-none last:rounded-b-xl md:last:rounded-r-xl md:last:rounded-bl-none">
                {i < 2 && (
                  <div className="hidden md:flex absolute -right-4 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-[#3251BC] text-white rounded-full items-center justify-center text-xs">
                    &rarr;
                  </div>
                )}
                <div className="text-3xl mb-3">{s.icon}</div>
                <div className="w-10 h-10 bg-gradient-to-br from-[#3251BC] to-[#5a7be0] text-white rounded-full flex items-center justify-center text-sm font-black mx-auto mb-3 shadow-md">{s.step}</div>
                <h3 className="text-base font-bold text-[#333] mb-2">{s.title}</h3>
                <p className="text-sm text-[#666] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────── */}
      <section className="bg-gradient-to-b from-[#eef2fb] to-[#dce4f5] py-14 md:py-18">
        <div className="max-w-[960px] mx-auto px-5 text-center">
          <h2 className="text-xl md:text-2xl font-black text-[#222] mb-3">
            今すぐ、全レースの<br className="md:hidden" />ランク指数を確認しよう
          </h2>
          <p className="text-sm md:text-base text-[#666] mb-8">
            独自AI分析 × 8つの分析項目 × JRA全レース
          </p>
          <a
            href={LINE_ADD_URL}
            className="inline-flex items-center gap-2.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
            LINEでログインして始める
          </a>
          <p className="text-xs text-[#999] mt-4">完全無料 · 登録不要 · すぐ使える</p>
        </div>
      </section>
    </div>
  );
}
