"use client";

export default function TasksPage() {
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">任务管理</h1>
        <button className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          创建任务
        </button>
      </div>
      <div className="mt-4 flex space-x-2">
        {["全部", "待开始", "运行中", "已完成", "已失败"].map((tab) => (
          <button
            key={tab}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="mt-4 rounded-xl border border-gray-200 bg-white">
        <div className="p-6 text-center text-sm text-gray-400">暂无任务</div>
      </div>
    </div>
  );
}
