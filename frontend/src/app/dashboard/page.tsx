"use client";

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900">概览</h1>
      <p className="mt-2 text-sm text-gray-500">欢迎使用龙蟾GEO系统</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "品牌数", value: "-" },
          { label: "问题集数", value: "-" },
          { label: "进行中任务", value: "-" },
          { label: "已完成任务", value: "-" },
        ].map((card) => (
          <div key={card.label} className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{card.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
