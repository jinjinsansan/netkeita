"use client";

import Link from "next/link";
import RankBadge from "@/components/RankBadge";
import type { Grade } from "@/lib/types";

const LINE_ADD_URL = "#"; // TODO: LINE Login URL

// Demo data for the matrix preview
const DEMO_HORSES: {
  post: number;
  number: number;
  name: string;
  jockey: string;
  ranks: Record<string, Grade>;
}[] = [
  { post: 5, number: 7, name: "ショウナンバルディ", jockey: "C.ルメール", ranks: { total: "S", speed: "A", flow: "S", jockey: "A", bloodline: "S", recent: "A", track: "B", ev: "S" } },
  { post: 3, number: 4, name: "タイセイドリーマー", jockey: "川田将雅", ranks: { total: "A", speed: "S", flow: "A", jockey: "S", bloodline: "A", recent: "B", track: "A", ev: "A" } },
  { post: 7, number: 12, name: "メイショウハリオ", jockey: "武豊", ranks: { total: "A", speed: "A", flow: "B", jockey: "A", bloodline: "B", recent: "S", track: "A", ev: "B" } },
  { post: 1, number: 1, name: "ドゥラエレーデ", jockey: "戸崎圭太", ranks: { total: "B", speed: "B", flow: "A", jockey: "B", bloodline: "A", recent: "A", track: "S", ev: "A" } },
  { post: 4, number: 6, name: "ウインマリリン", jockey: "松山弘平", ranks: { total: "B", speed: "C", flow: "B", jockey: "A", bloodline: "B", recent: "B", track: "B", ev: "C" } },
  { post: 8, number: 14, name: "テーオーロイヤル", jockey: "横山武史", ranks: { total: "C", speed: "B", flow: "C", jockey: "B", bloodline: "C", recent: "C", track: "A", ev: "B" } },
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
  { key: "total", label: "総合" },
  { key: "speed", label: "速度" },
  { key: "flow", label: "展開" },
  { key: "jockey", label: "騎手" },
  { key: "bloodline", label: "血統" },
  { key: "recent", label: "近走" },
  { key: "track", label: "馬場" },
  { key: "ev", label: "EV" },
];

const FEATURES = [
  {
    icon: "📊",
    title: "8項目のランク指数",
    desc: "総合・スピード・展開・騎手・血統・近走・馬場・期待値。すべての要素をS〜Dの5段階で一目で把握。",
  },
  {
    icon: "🏇",
    title: "JRA全レース対応",
    desc: "毎週の土日JRA全レースを網羅。出走全馬のランクをリアルタイムで確認できます。",
  },
  {
    icon: "🤖",
    title: "4つの独立AIエンジン",
    desc: "D-Logic / I-Logic / MetaLogic / ViewLogic。4エンジンが独立に分析し、多角的な指数を生成。",
  },
  {
    icon: "📱",
    title: "モバイルファースト",
    desc: "スマホで直感的に操作できる横スクロール表示。通勤中でもパドックでもサッと確認。",
  },
  {
    icon: "🎯",
    title: "期待値（EV）表示",
    desc: "AIの予測勝率とオッズから算出した期待値を表示。回収率を意識した馬券戦略をサポート。",
  },
  {
    icon: "🆓",
    title: "完全無料",
    desc: "LINEログインだけですべての機能が使えます。課金要素は一切ありません。",
  },
];

const HOW_TO_STEPS = [
  { step: "01", title: "LINEでログイン", desc: "お持ちのLINEアカウントでワンタップログイン。面倒な登録は不要。" },
  { step: "02", title: "レースを選ぶ", desc: "日付・競馬場・R番号で今週のレースを選択。" },
  { step: "03", title: "ランク指数を見る", desc: "8項目のランクマトリクスで全馬を一覧比較。直感的に有力馬を把握。" },
];

export default function LandingPage() {
  return (
    <div className="bg-white">
      {/* ── Hero Section ─────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-[#f8faf8] to-white">
        <div className="max-w-[960px] mx-auto px-4 pt-12 pb-8 md:pt-20 md:pb-14 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 bg-[#e8f5e9] text-[#1f7a1f] text-[11px] font-bold px-3 py-1 rounded-full mb-5">
            <span className="w-1.5 h-1.5 bg-[#1f7a1f] rounded-full animate-pulse" />
            完全無料 · LINEログインですぐ使える
          </div>

          <h1 className="text-2xl md:text-4xl font-black text-[#222] leading-tight mb-4">
            JRA全レースを<br className="md:hidden" />
            <span className="text-[#1f7a1f]">8つの指数</span>で<br className="md:hidden" />
            可視化する
          </h1>
          <p className="text-sm md:text-base text-[#666] max-w-lg mx-auto mb-8 leading-relaxed">
            総合・スピード・展開・騎手・血統・近走・馬場・期待値。<br className="hidden md:block" />
            4つのAIエンジンが生成するランク指数で、全馬を一目で比較。
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-10">
            <a
              href={LINE_ADD_URL}
              className="flex items-center gap-2 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-sm px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition-all"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
              </svg>
              LINEでログインして見る
            </a>
            <span className="text-[11px] text-[#999]">登録不要 · 30秒で完了</span>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-6 md:gap-10 text-center mb-8">
            {[
              { value: "4", label: "独立AIエンジン" },
              { value: "8", label: "分析項目" },
              { value: "959K+", label: "レースデータ" },
            ].map((stat) => (
              <div key={stat.label}>
                <p className="text-xl md:text-3xl font-black text-[#1f7a1f]">{stat.value}</p>
                <p className="text-[10px] md:text-xs text-[#888]">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo Matrix Section (netkeiba style) ─────── */}
      <section className="bg-[#f5f5f5] py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-6">
            <h2 className="text-lg md:text-2xl font-black text-[#222] mb-2">
              ランクマトリクスで<span className="text-[#1f7a1f]">一目瞭然</span>
            </h2>
            <p className="text-xs md:text-sm text-[#888]">
              出走全馬の8項目を横スクロールで比較。有力馬が即座にわかる。
            </p>
          </div>

          {/* netkeiba style race header */}
          <div className="border border-[#c6c9d3] rounded-t bg-white">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-[#e0e0e0] bg-[#f5f5f5]">
              <span className="bg-[#1f7a1f] text-white text-[11px] font-bold px-2 py-0.5 rounded">
                11R
              </span>
              <span className="text-sm font-bold text-[#333]">大阪杯 GⅠ</span>
            </div>
            <div className="px-3 py-1.5 text-[11px] text-[#555] flex flex-wrap gap-x-3">
              <span>阪神</span>
              <span>芝2000m</span>
              <span>馬場: 良</span>
              <span>16頭</span>
            </div>
          </div>

          {/* Matrix table */}
          <div className="overflow-x-auto border border-t-0 border-[#c6c9d3] rounded-b bg-white">
            <table className="nk-table">
              <thead>
                <tr>
                  <th className="w-8 !text-[10px]">枠</th>
                  <th className="w-8 !text-[10px]">番</th>
                  <th className="min-w-[100px] text-left !text-[10px]">馬名</th>
                  <th className="w-16 !text-[10px]">騎手</th>
                  {RANK_COLS.map((col) => (
                    <th key={col.key} className="w-[34px] !text-[10px]">{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DEMO_HORSES.map((horse) => (
                  <tr key={horse.number}>
                    <td className="text-center">
                      <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold ${WAKU_BG[horse.post] || ""}`}>
                        {horse.post}
                      </span>
                    </td>
                    <td className="text-center font-bold text-xs">{horse.number}</td>
                    <td className="text-left text-xs font-medium whitespace-nowrap">{horse.name}</td>
                    <td className="text-center text-[10px] text-[#555] whitespace-nowrap">{horse.jockey}</td>
                    {RANK_COLS.map((col) => (
                      <td key={col.key} className="text-center">
                        <RankBadge grade={horse.ranks[col.key]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-[#888]">
            {[
              { grade: "S", label: "1位", bg: "#FFD700", text: "#333" },
              { grade: "A", label: "上位25%", bg: "#E53935", text: "#fff" },
              { grade: "B", label: "上位50%", bg: "#1E88E5", text: "#fff" },
              { grade: "C", label: "上位75%", bg: "#43A047", text: "#fff" },
              { grade: "D", label: "下位25%", bg: "#9E9E9E", text: "#fff" },
            ].map((r) => (
              <span key={r.grade} className="flex items-center gap-1">
                <span
                  className="w-4 h-4 rounded-sm text-center leading-4 font-bold text-[9px] inline-block"
                  style={{ backgroundColor: r.bg, color: r.text }}
                >
                  {r.grade}
                </span>
                {r.label}
              </span>
            ))}
          </div>

          {/* Blur overlay CTA */}
          <div className="mt-5 text-center">
            <p className="text-xs text-[#888] mb-2">
              ※ 上記はサンプルデータです。ログインすると今週の全レースが閲覧できます。
            </p>
          </div>
        </div>
      </section>

      {/* ── Features Section ─────────────────────────── */}
      <section className="py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-8">
            <h2 className="text-lg md:text-2xl font-black text-[#222] mb-2">
              netkeita の<span className="text-[#1f7a1f]">特長</span>
            </h2>
            <p className="text-xs md:text-sm text-[#888]">
              予想サイトではなく「データ閲覧サイト」。数値で判断するあなたのための競馬ツール。
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="border border-[#e0e0e0] rounded-lg p-5 bg-white hover:border-[#1f7a1f] hover:shadow-sm transition"
              >
                <div className="text-2xl mb-2">{f.icon}</div>
                <h3 className="text-sm font-bold text-[#333] mb-1">{f.title}</h3>
                <p className="text-[11px] text-[#888] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 8 Rank Items Detail ──────────────────────── */}
      <section className="bg-[#f8faf8] py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-8">
            <h2 className="text-lg md:text-2xl font-black text-[#222] mb-2">
              <span className="text-[#1f7a1f]">8項目</span>のランク指数
            </h2>
            <p className="text-xs md:text-sm text-[#888]">
              各項目を出走馬全頭の相対順位でS〜Dにランク付け
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { key: "total", label: "総合", grade: "S" as Grade, engine: "MetaLogic", desc: "4エンジンの統合スコア" },
              { key: "speed", label: "スピード", grade: "A" as Grade, engine: "D-Logic", desc: "10項目の独自指数" },
              { key: "flow", label: "展開", grade: "A" as Grade, engine: "ViewLogic", desc: "脚質・先行力の分析" },
              { key: "jockey", label: "騎手", grade: "S" as Grade, engine: "統計", desc: "コース別複勝率" },
              { key: "bloodline", label: "血統", grade: "B" as Grade, engine: "統計", desc: "父・母父のコース適性" },
              { key: "recent", label: "近走", grade: "A" as Grade, engine: "直近5走", desc: "着順平均+トレンド" },
              { key: "track", label: "馬場", grade: "B" as Grade, engine: "3層補正", desc: "馬場適性の補正係数" },
              { key: "ev", label: "期待値", grade: "S" as Grade, engine: "EV算出", desc: "予測勝率÷オッズ" },
            ].map((item) => (
              <div key={item.key} className="border border-[#e0e0e0] rounded-lg p-4 bg-white text-center">
                <RankBadge grade={item.grade} />
                <h3 className="text-sm font-bold text-[#333] mt-2 mb-0.5">{item.label}</h3>
                <p className="text-[10px] text-[#1f7a1f] font-medium mb-1">{item.engine}</p>
                <p className="text-[10px] text-[#888]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How to Use ───────────────────────────────── */}
      <section className="py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-8">
            <h2 className="text-lg md:text-2xl font-black text-[#222] mb-2">
              使い方は<span className="text-[#1f7a1f]">3ステップ</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {HOW_TO_STEPS.map((s) => (
              <div key={s.step} className="text-center border border-[#e0e0e0] rounded-lg p-6 bg-white">
                <div className="w-10 h-10 bg-[#1f7a1f] text-white rounded-full flex items-center justify-center text-sm font-black mx-auto mb-3">
                  {s.step}
                </div>
                <h3 className="text-sm font-bold text-[#333] mb-1">{s.title}</h3>
                <p className="text-[11px] text-[#888] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────── */}
      <section className="bg-gradient-to-b from-[#f0f7f0] to-[#e8f5e9] py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-4 text-center">
          <h2 className="text-lg md:text-2xl font-black text-[#222] mb-3">
            今すぐ、全レースの<br className="md:hidden" />
            ランク指数を確認しよう
          </h2>
          <p className="text-xs md:text-sm text-[#666] mb-6">
            4つのAIエンジン × 8つの分析項目 × JRA全レース
          </p>

          <a
            href={LINE_ADD_URL}
            className="inline-flex items-center gap-2 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-sm px-8 py-3.5 rounded-lg shadow-md hover:shadow-lg transition-all"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
            </svg>
            LINEでログインして始める
          </a>
          <p className="text-[10px] text-[#999] mt-3">
            完全無料 · 登録不要 · すぐ使える
          </p>
        </div>
      </section>
    </div>
  );
}
