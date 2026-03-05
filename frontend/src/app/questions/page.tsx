"use client";

export default function QuestionsPage() {
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">问题管理</h1>
        <button className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          新建问题集
        </button>
      </div>
      <div className="mt-6 rounded-xl border border-gray-200 bg-white">
        <div className="p-6 text-center text-sm text-gray-400">暂无问题集</div>
      </div>
    </div>
  );
}
