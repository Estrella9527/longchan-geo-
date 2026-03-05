"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "首页" },
  { href: "/brands", label: "品牌" },
  { href: "/questions", label: "问题" },
  { href: "/tasks", label: "任务" },
  { href: "/analysis", label: "分析" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-400">加载中...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-gray-200 bg-white">
        <div className="flex h-14 items-center border-b border-gray-200 px-5">
          <span className="text-lg font-bold text-primary-600">灵渡GEO</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition",
                pathname.startsWith(item.href)
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-100"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-gray-200 p-4">
          <div className="text-xs text-gray-400">{user?.display_name || user?.username}</div>
          <button onClick={logout} className="mt-2 text-xs text-gray-500 hover:text-red-500">
            退出登录
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
          <div className="flex items-center space-x-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "text-sm font-medium transition",
                  pathname.startsWith(item.href) ? "text-primary-600" : "text-gray-500 hover:text-gray-900"
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-500">{user?.display_name}</span>
          </div>
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
