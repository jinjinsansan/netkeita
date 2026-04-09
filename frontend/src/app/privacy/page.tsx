import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "プライバシーポリシー | netkeita",
  description: "netkeita のプライバシーポリシーです。",
  robots: { index: true, follow: true },
};

const LAST_UPDATED = "2026年4月9日";

export default function PrivacyPage() {
  return (
    <div className="max-w-[760px] mx-auto px-4 py-10">
      <div className="text-[11px] text-[#666] mb-6 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">トップ</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>プライバシーポリシー</span>
      </div>

      <h1 className="text-2xl font-black text-[#1a1a1a] mb-2">プライバシーポリシー</h1>
      <p className="text-[12px] text-[#999] mb-8">最終更新日：{LAST_UPDATED}</p>

      <div className="prose-nk space-y-8">

        <section>
          <h2>1. はじめに</h2>
          <p>
            netkeita（以下「当サービス」）は、ユーザーの個人情報の取り扱いについて、以下のプライバシーポリシー（以下「本ポリシー」）を定めます。当サービスをご利用いただく際には、本ポリシーをお読みください。
          </p>
        </section>

        <section>
          <h2>2. 収集する情報</h2>
          <p>当サービスは、以下の情報を収集することがあります。</p>
          <h3>2-1. LINEログインを通じて取得する情報</h3>
          <p>
            当サービスでは、LINE株式会社が提供する「LINEログイン」を利用しています。ログイン時に、LINEアカウントに紐づく以下の情報を取得します。
          </p>
          <ul>
            <li>LINEユーザーID</li>
            <li>表示名（ニックネーム）</li>
            <li>プロフィール画像URL</li>
          </ul>
          <p>
            パスワードや電話番号、メールアドレスは取得しません。
          </p>
          <h3>2-2. 利用履歴情報</h3>
          <p>
            当サービスのご利用にあたり、以下の情報をサーバー上に記録する場合があります。
          </p>
          <ul>
            <li>投票・予想の履歴（レースID・馬番）</li>
            <li>Kリワードポイントの残高・履歴</li>
            <li>アクセスログ（IPアドレス、ブラウザ情報、アクセス日時）</li>
          </ul>
        </section>

        <section>
          <h2>3. 情報の利用目的</h2>
          <p>収集した情報は、以下の目的に限り利用します。</p>
          <ul>
            <li>ログイン状態の維持およびユーザー認証</li>
            <li>みんなの予想（投票）機能の提供</li>
            <li>Kリワードポイントの管理</li>
            <li>サービス改善のための統計分析</li>
            <li>不正利用の防止</li>
            <li>お問い合わせへの対応</li>
          </ul>
        </section>

        <section>
          <h2>4. 第三者への提供</h2>
          <p>
            当サービスは、以下の場合を除き、取得した個人情報を第三者へ提供しません。
          </p>
          <ul>
            <li>ユーザー本人の同意がある場合</li>
            <li>法令に基づき開示が必要な場合</li>
            <li>人の生命・財産の保護のために必要で、本人の同意を得ることが困難な場合</li>
          </ul>
        </section>

        <section>
          <h2>5. 外部サービスの利用</h2>
          <p>当サービスは以下の外部サービスを利用しており、それぞれのプライバシーポリシーが適用されます。</p>
          <ul>
            <li>
              <strong>LINE（LINEログイン）</strong>：
              <a href="https://line.me/ja/terms/policy/" target="_blank" rel="noopener noreferrer">
                LINEプライバシーポリシー
              </a>
            </li>
            <li>
              <strong>Vercel</strong>（フロントエンドホスティング）：アクセスログが収集される場合があります。
            </li>
          </ul>
        </section>

        <section>
          <h2>6. Cookieおよびローカルストレージ</h2>
          <p>
            当サービスは、ログイン状態の維持のためにブラウザのローカルストレージにセッショントークンを保存します。このトークンはログアウト時またはブラウザのデータ消去時に削除されます。
          </p>
          <p>
            アクセス解析などの目的でCookieを利用する場合があります。ブラウザの設定によりCookieを無効にすることができますが、一部機能が利用できなくなる場合があります。
          </p>
        </section>

        <section>
          <h2>7. データの保存期間</h2>
          <p>
            セッション情報はログインから30日間（最終アクセスより自動延長）保存されます。投票履歴およびKリワード履歴は最終記録から90日間保存されます。
          </p>
        </section>

        <section>
          <h2>8. 個人情報の開示・訂正・削除</h2>
          <p>
            ユーザーご本人から個人情報の開示・訂正・削除のご要望がある場合は、下記お問い合わせ窓口よりご連絡ください。本人確認の上、合理的な範囲で対応いたします。
          </p>
        </section>

        <section>
          <h2>9. 未成年者の利用</h2>
          <p>
            公営競技（競馬）への参加は20歳以上の方が対象です。当サービスはデータ閲覧・分析ツールとして提供しており、馬券の購入を仲介するものではありませんが、20歳未満の方のご利用については保護者の同意を得たうえでご利用ください。
          </p>
        </section>

        <section>
          <h2>10. 本ポリシーの変更</h2>
          <p>
            当サービスは、必要に応じて本ポリシーを変更することがあります。変更後のポリシーは本ページに掲載した時点で効力を生じます。
          </p>
        </section>

        <section>
          <h2>11. お問い合わせ</h2>
          <p>
            本ポリシーに関するお問い合わせは、LINEの公式アカウントまたはサービス内のお問い合わせ窓口よりご連絡ください。
          </p>
        </section>

      </div>

      <div className="mt-12 pt-6 border-t border-[#e5e5e5]">
        <Link href="/" className="text-xs font-bold text-[#1f7a1f] hover:underline">
          ← トップページへ戻る
        </Link>
      </div>
    </div>
  );
}
