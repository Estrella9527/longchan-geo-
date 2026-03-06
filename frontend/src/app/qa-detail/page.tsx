"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/data-table";
import { Search, Download, Eye, ExternalLink } from "lucide-react";
import { taskApi, analysisApi } from "@/lib/api";
import type { Task, TaskResult } from "@/types";

const columns: ColumnDef<TaskResult>[] = [
  { accessorKey: "created_at", header: "时间", cell: ({ row }) => new Date(row.getValue("created_at") as string).toLocaleString("zh-CN") },
  { accessorKey: "model_name", header: "模型", cell: ({ row }) => <Badge variant="outline">{row.getValue("model_name") as string || "-"}</Badge> },
  { accessorKey: "model_version", header: "版本", cell: ({ row }) => (row.getValue("model_version") as string) || "-" },
  { accessorKey: "question_text", header: "问题", cell: ({ row }) => <div className="max-w-[200px] truncate">{row.getValue("question_text")}</div> },
  { accessorKey: "answer_text", header: "回答", cell: ({ row }) => <div className="max-w-[300px] truncate">{row.getValue("answer_text")}</div> },
  {
    accessorKey: "sources", header: "信息源",
    cell: ({ row }) => {
      const sources = row.getValue("sources");
      const count = Array.isArray(sources) ? sources.length : 0;
      return <Badge variant="secondary">{count} 条</Badge>;
    },
  },
];

export default function QADetailPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [results, setResults] = useState<TaskResult[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [loading, setLoading] = useState(true);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return results;
    const q = searchQuery.toLowerCase();
    return results.filter(
      (r) => r.question_text.toLowerCase().includes(q) || r.answer_text.toLowerCase().includes(q)
    );
  }, [results, searchQuery]);

  useEffect(() => {
    taskApi.list().then((res) => setTasks(res.data)).catch(() => toast.error("加载任务列表失败")).finally(() => setLoading(false));
  }, []);

  const fetchResults = useCallback(async (taskId: string) => {
    if (!taskId) { setResults([]); return; }
    setResultsLoading(true);
    try {
      const res = await taskApi.results(taskId);
      setResults(res.data);
    } catch {
      toast.error("加载问答结果失败");
    } finally {
      setResultsLoading(false);
    }
  }, []);

  useEffect(() => { fetchResults(selectedTaskId); }, [selectedTaskId, fetchResults]);

  if (loading) {
    return <div className="space-y-4"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">问答明细</h1>
          <p className="text-sm text-muted-foreground">查看任务的问答回收结果和信息源</p>
        </div>
        <Button
          variant="outline"
          disabled={!selectedTaskId || results.length === 0}
          onClick={async () => {
            try {
              const res = await analysisApi.exportCsv(selectedTaskId);
              const url = window.URL.createObjectURL(new Blob([res.data]));
              const a = document.createElement("a");
              a.href = url;
              a.download = `task_${selectedTaskId}_results.csv`;
              a.click();
              window.URL.revokeObjectURL(url);
              toast.success("导出成功");
            } catch {
              toast.error("导出失败");
            }
          }}
        >
          <Download className="mr-2 h-4 w-4" />
          导出数据
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={selectedTaskId} onValueChange={setSelectedTaskId}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="选择任务" />
          </SelectTrigger>
          <SelectContent>
            {tasks.length === 0 ? <SelectItem value="none" disabled>暂无任务</SelectItem>
              : tasks.map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="搜索问题或回答..." className="pl-9" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
        </div>
        {selectedTaskId && <Badge variant="secondary">共 {filteredResults.length} 条结果{searchQuery && filteredResults.length !== results.length ? ` (筛选自 ${results.length} 条)` : ""}</Badge>}
      </div>

      {resultsLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <DataTable columns={columns} data={filteredResults} emptyMessage={selectedTaskId ? (searchQuery ? "无匹配结果" : "该任务暂无问答结果") : "请选择任务查看问答明细"} />
      )}
    </div>
  );
}
