import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "特定商取引法に基づく表記 | netkeita",
  description: "netkeita（ネットケイタ）の特定商取引法に基づく表記ページです。",
};

const ROWS: [string, string][] = [
  ["販売業者", "合同会社KK企画"],
  ["運営統括責任者", "笹栗啓太"],
  ["所在地", "札幌市豊平区平岸1条6丁目1-25-501"],
  ["お問い合わせ", "公式LINEにてお受けしております"],
  ["販売価格", "各有料コンテンツに記載の金額"],
  ["商品代金以外の必要料金", "なし"],
  ["支払方法", "クレジットカード等"],
  ["支払時期", "購入手続き完了時に即時決済"],
  ["商品の引渡し時期", "決済完了後、即時閲覧可能"],
  ["返品・交換", "デジタルコンテンツの性質上、購入後の返品・返金は原則不可"],
  ["動作環境", "モダンブラウザ（Chrome, Safari, Edge 等の最新版）"],
];

export default function TradelawPage() {
  return (
    <div className="max-w-[960px] mx-auto px-4 py-10">
      <h1 className="text-xl font-black text-[#222] mb-6">特定商取引法に基づく表記</h1>

      <div className="border border-[#c6c9d3] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <tbody>
            {ROWS.map(([label, value], i) => (
              <tr
                key={label}
                className={i % 2 === 0 ? "bg-white" : "bg-[#f9f9f9]"}
              >
                <th className="text-left font-bold text-[#222] py-3 px-4 align-top whitespace-nowrap w-44 border-b border-[#e5e5e5]">
                  {label}
                </th>
                <td className="py-3 px-4 text-[#444] border-b border-[#e5e5e5]">
                  {value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
