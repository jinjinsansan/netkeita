"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { loading, authenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !authenticated) {
      localStorage.setItem("nk_redirect", pathname);
      router.replace("/login");
    }
  }, [loading, authenticated, router, pathname]);

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center text-[#888] text-sm">
        認証確認中...
      </div>
    );
  }

  if (!authenticated) return null;

  return <>{children}</>;
}
