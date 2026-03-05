"use client";

export default function AnalysisPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900">分析解读</h1>
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {["品牌可见性", "排名水平", "情感分析", "竞品分析"].map((title) => (
          <div key={title} className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="text-sm font-medium text-gray-700">{title}</h3>
            <div className="mt-4 flex h-48 items-center justify-center text-sm text-gray-400">
              图表区域
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
