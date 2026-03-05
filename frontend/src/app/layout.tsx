import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "龙蟾GEO系统",
  description: "灵渡GEO - AI意图与品牌监测平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
