"use client";

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
    desc: "総合・スピード・展開・騎手・血統・近走・馬場・期待値。すべての要素をS〜Dで一目把握。",
  },
  {
    icon: "🏇",
    title: "JRA全レース対応",
    desc: "毎週の土日JRA全レースを網羅。出走全馬のランクをリアルタイムで確認できます。",
  },
  {
    icon: "🤖",
    title: "独自の複合AI分析",
    desc: "複数の独立したAIエンジンがそれぞれ異なる角度から分析し、多角的な指数を生成。",
  },
  {
    icon: "📱",
    title: "モバイルファースト",
    desc: "スマホで直感的に操作できる横スクロール表示。通勤中でもパドックでもサッと確認。",
  },
  {
    icon: "🎯",
    title: "期待値（EV）表示",
    desc: "AI予測勝率とオッズから算出した期待値を表示。回収率を意識した馬券戦略をサポート。",
  },
  {
    icon: "🆓",
    title: "完全無料",
    desc: "LINEログインだけですべての機能が使えます。課金要素は一切ありません。",
  },
];

const HOW_TO_STEPS = [
  { step: "01", title: "LINEでログイン", desc: "お持ちのLINEアカウントでワンタップログイン。面倒な登録は不要です。" },
  { step: "02", title: "レースを選ぶ", desc: "日付・競馬場・R番号で今週のレースをかんたん選択。" },
  { step: "03", title: "ランク指数を見る", desc: "8項目のランクマトリクスで全馬を一覧比較。有力馬が直感的にわかる。" },
];

export default function LandingPage() {
  return (
    <div className="bg-white">
      {/* ── Hero Section ─────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-[#f8faf8] to-white">
        <div className="max-w-[960px] mx-auto px-5 pt-14 pb-10 md:pt-20 md:pb-14 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 bg-[#e8f5e9] text-[#1f7a1f] text-xs font-bold px-4 py-1.5 rounded-full mb-6">
            <span className="w-2 h-2 bg-[#1f7a1f] rounded-full animate-pulse" />
            完全無料 · LINEログインですぐ使える
          </div>

          <h1 className="text-[28px] md:text-[42px] font-black text-[#222] leading-[1.3] mb-5">
            JRA全レースを<br className="md:hidden" />
            <span className="text-[#1f7a1f]">8つの指数</span>で<br className="md:hidden" />
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
              <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
              </svg>
              LINEでログインして見る
            </a>
            <span className="text-xs text-[#999]">登録不要 · 30秒で完了</span>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-8 md:gap-12 text-center mb-6">
            {[
              { value: "全レース", label: "JRA土日対応" },
              { value: "8", label: "分析項目" },
              { value: "5段階", label: "ランク評価" },
            ].map((stat) => (
              <div key={stat.label}>
                <p className="text-2xl md:text-3xl font-black text-[#1f7a1f]">{stat.value}</p>
                <p className="text-xs md:text-sm text-[#888] mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo Matrix Section (netkeiba style) ─────── */}
      <section className="bg-[#f5f5f5] py-10 md:py-14">
        <div className="max-w-[960px] mx-auto px-4">
          <div className="text-center mb-6">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              ランクマトリクスで<span className="text-[#1f7a1f]">一目瞭然</span>
            </h2>
            <p className="text-sm md:text-base text-[#888]">
              出走全馬の8項目を横スクロールで比較
            </p>
          </div>

          {/* netkeiba style race header */}
          <div className="border border-[#c6c9d3] rounded-t bg-white">
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#e0e0e0] bg-[#f5f5f5]">
              <span className="bg-[#1f7a1f] text-white text-xs font-bold px-2.5 py-0.5 rounded">
                11R
              </span>
              <span className="text-base font-bold text-[#333]">大阪杯 GⅠ</span>
            </div>
            <div className="px-3 py-2 text-xs text-[#555] flex flex-wrap gap-x-3">
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
                  <th className="w-9">枠</th>
                  <th className="w-9">番</th>
                  <th className="min-w-[110px] text-left">馬名</th>
                  <th className="w-[70px]">騎手</th>
                  {RANK_COLS.map((col) => (
                    <th key={col.key} className="w-[38px]">{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DEMO_HORSES.map((horse) => (
                  <tr key={horse.number}>
                    <td className="text-center">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${WAKU_BG[horse.post] || ""}`}>
                        {horse.post}
                      </span>
                    </td>
                    <td className="text-center font-bold text-sm">{horse.number}</td>
                    <td className="text-left text-sm font-medium whitespace-nowrap">{horse.name}</td>
                    <td className="text-center text-xs text-[#555] whitespace-nowrap">{horse.jockey}</td>
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
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-[#888]">
            {[
              { grade: "S", label: "1位", bg: "#FFD700", text: "#333" },
              { grade: "A", label: "上位25%", bg: "#E53935", text: "#fff" },
              { grade: "B", label: "上位50%", bg: "#1E88E5", text: "#fff" },
              { grade: "C", label: "上位75%", bg: "#43A047", text: "#fff" },
              { grade: "D", label: "下位25%", bg: "#9E9E9E", text: "#fff" },
            ].map((r) => (
              <span key={r.grade} className="flex items-center gap-1">
                <span
                  className="w-5 h-5 rounded-sm text-center leading-5 font-bold text-[10px] inline-block"
                  style={{ backgroundColor: r.bg, color: r.text }}
                >
                  {r.grade}
                </span>
                {r.label}
              </span>
            ))}
          </div>

          <div className="mt-5 text-center">
            <p className="text-sm text-[#888]">
              ※ サンプルデータです。ログインすると今週の全レースが閲覧できます。
            </p>
          </div>
        </div>
      </section>

      {/* ── Features Section ─────────────────────────── */}
      <section id="features" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              netkeita の<span className="text-[#1f7a1f]">特長</span>
            </h2>
            <p className="text-sm md:text-base text-[#888]">
              予想サイトではなく「データ閲覧サイト」
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="border border-[#e0e0e0] rounded-lg p-5 bg-white hover:border-[#1f7a1f] hover:shadow-sm transition"
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="text-base font-bold text-[#333] mb-1.5">{f.title}</h3>
                <p className="text-sm text-[#888] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 8 Rank Items Detail ──────────────────────── */}
      <section className="bg-[#f8faf8] py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              <span className="text-[#1f7a1f]">8項目</span>のランク指数
            </h2>
            <p className="text-sm md:text-base text-[#888]">
              各項目を出走馬全頭の相対順位でS〜Dにランク付け
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { key: "total", label: "総合", grade: "S" as Grade, engine: "統合スコア", desc: "全エンジンの総合評価" },
              { key: "speed", label: "スピード", grade: "A" as Grade, engine: "能力指数", desc: "10項目の独自スコア" },
              { key: "flow", label: "展開", grade: "A" as Grade, engine: "展開予測", desc: "脚質・先行力の分析" },
              { key: "jockey", label: "騎手", grade: "S" as Grade, engine: "騎手統計", desc: "コース別複勝率" },
              { key: "bloodline", label: "血統", grade: "B" as Grade, engine: "血統統計", desc: "父・母父のコース適性" },
              { key: "recent", label: "近走", grade: "A" as Grade, engine: "直近5走", desc: "着順平均+トレンド" },
              { key: "track", label: "馬場", grade: "B" as Grade, engine: "馬場補正", desc: "馬場適性の補正係数" },
              { key: "ev", label: "期待値", grade: "S" as Grade, engine: "EV算出", desc: "予測勝率÷オッズ" },
            ].map((item) => (
              <div key={item.key} className="border border-[#e0e0e0] rounded-lg p-4 bg-white text-center">
                <RankBadge grade={item.grade} />
                <h3 className="text-base font-bold text-[#333] mt-2 mb-1">{item.label}</h3>
                <p className="text-xs text-[#1f7a1f] font-medium mb-1">{item.engine}</p>
                <p className="text-xs text-[#888]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How to Use ───────────────────────────────── */}
      <section id="howto" className="py-12 md:py-16">
        <div className="max-w-[960px] mx-auto px-5">
          <div className="text-center mb-8">
            <h2 className="text-xl md:text-2xl font-black text-[#222] mb-2">
              使い方は<span className="text-[#1f7a1f]">3ステップ</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {HOW_TO_STEPS.map((s) => (
              <div key={s.step} className="text-center border border-[#e0e0e0] rounded-lg p-6 bg-white">
                <div className="w-12 h-12 bg-[#1f7a1f] text-white rounded-full flex items-center justify-center text-base font-black mx-auto mb-4">
                  {s.step}
                </div>
                <h3 className="text-base font-bold text-[#333] mb-2">{s.title}</h3>
                <p className="text-sm text-[#888] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────── */}
      <section className="bg-gradient-to-b from-[#f0f7f0] to-[#e8f5e9] py-14 md:py-18">
        <div className="max-w-[960px] mx-auto px-5 text-center">
          <h2 className="text-xl md:text-2xl font-black text-[#222] mb-3">
            今すぐ、全レースの<br className="md:hidden" />
            ランク指数を確認しよう
          </h2>
          <p className="text-sm md:text-base text-[#666] mb-8">
            独自AI分析 × 8つの分析項目 × JRA全レース
          </p>

          <a
            href={LINE_ADD_URL}
            className="inline-flex items-center gap-2.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-base px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
            </svg>
            LINEでログインして始める
          </a>
          <p className="text-xs text-[#999] mt-4">
            完全無料 · 登録不要 · すぐ使える
          </p>
        </div>
      </section>
    </div>
  );
}
