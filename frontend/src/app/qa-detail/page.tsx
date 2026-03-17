"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search, Download, ChevronDown, ChevronRight, ExternalLink, FileText, Globe, Clock,
} from "lucide-react";
import { taskApi, analysisApi } from "@/lib/api";
import type { Task, TaskResult, CrawledPage } from "@/types";

const providerLabels: Record<string, string> = {
  api: "API",
  browser_doubao: "豆包",
  browser_deepseek: "DeepSeek",
};

const sourceTypeLabels: Record<string, string> = {
  parsed: "正则解析",
  crawled: "浏览器抓取",
};

/** Extract domain from URL for display when title is missing */
function getDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/** Render answer text with basic formatting (paragraphs, lists) */
function FormattedAnswer({ text }: { text: string }) {
  if (!text) return <p className="text-sm text-muted-foreground">无回答内容</p>;

  const paragraphs = text.split(/\n\n+/);

  return (
    <div className="text-sm leading-relaxed space-y-3">
      {paragraphs.map((para, pi) => {
        const trimmed = para.trim();
        if (!trimmed) return null;

        // Check if this paragraph is a list (lines starting with 1. / - / • / *)
        const lines = trimmed.split("\n");
        const isOrderedList = lines.length > 1 && lines.every((l) => /^\s*\d+[\.\)、]\s/.test(l));
        const isUnorderedList = lines.length > 1 && lines.every((l) => /^\s*[-•\*]\s/.test(l));

        if (isOrderedList) {
          return (
            <ol key={pi} className="list-decimal list-inside space-y-1">
              {lines.map((l, li) => (
                <li key={li}>{l.replace(/^\s*\d+[\.\)、]\s*/, "")}</li>
              ))}
            </ol>
          );
        }

        if (isUnorderedList) {
          return (
            <ul key={pi} className="list-disc list-inside space-y-1">
              {lines.map((l, li) => (
                <li key={li}>{l.replace(/^\s*[-•\*]\s*/, "")}</li>
              ))}
            </ul>
          );
        }

        // Check if it looks like a code block (indented or has backticks)
        if (trimmed.startsWith("```") || lines.every((l) => l.startsWith("    ") || l.startsWith("\t"))) {
          return (
            <pre key={pi} className="text-xs bg-muted/50 rounded p-3 overflow-x-auto whitespace-pre-wrap font-mono">
              {trimmed.replace(/^```\w*\n?/, "").replace(/\n?```$/, "")}
            </pre>
          );
        }

        // Regular paragraph — preserve single newlines
        return (
          <p key={pi} className="whitespace-pre-wrap">
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}

export default function QADetailPage() {
  const searchParams = useSearchParams();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [results, setResults] = useState<TaskResult[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState(searchParams.get("task") || "");
  const [loading, setLoading] = useState(true);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [crawledPages, setCrawledPages] = useState<CrawledPage[]>([]);
  const [crawledLoading, setCrawledLoading] = useState(false);
  const [detailResult, setDetailResult] = useState<TaskResult | null>(null);

  // Crawled pages for expanded row (separate from dialog)
  const [expandCrawled, setExpandCrawled] = useState<CrawledPage[]>([]);
  const [expandCrawledLoading, setExpandCrawledLoading] = useState(false);

  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return results;
    const q = searchQuery.toLowerCase();
    return results.filter(
      (r) => r.question_text.toLowerCase().includes(q) || r.answer_text.toLowerCase().includes(q)
    );
  }, [results, searchQuery]);

  // Get selected task info for empty state
  const selectedTask = useMemo(() => tasks.find((t) => t.id === selectedTaskId), [tasks, selectedTaskId]);

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

  const toggleExpand = async (resultId: string) => {
    if (expandedId === resultId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(resultId);
    setExpandCrawled([]);
    setExpandCrawledLoading(true);
    try {
      const res = await taskApi.crawledPages(resultId);
      setExpandCrawled(res.data);
    } catch {
      setExpandCrawled([]);
    } finally {
      setExpandCrawledLoading(false);
    }
  };

  const openDetail = async (result: TaskResult) => {
    setDetailResult(result);
    setCrawledPages([]);
    setCrawledLoading(true);
    try {
      const res = await taskApi.crawledPages(result.id);
      setCrawledPages(res.data);
    } catch {
      setCrawledPages([]);
    } finally {
      setCrawledLoading(false);
    }
  };

  if (loading) {
    return <div className="space-y-4"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">问答明细</h1>
          <p className="text-sm text-muted-foreground">查看任务的问答回收结果、信息源和爬取内容</p>
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
      ) : !selectedTaskId ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">请选择任务查看问答明细</CardContent></Card>
      ) : filteredResults.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {searchQuery ? "无匹配结果" : (
              selectedTask && (selectedTask.provider_type || "").startsWith("browser_")
                ? "该浏览器任务暂无问答结果，请检查会话登录状态是否正常"
                : "该任务暂无问答结果"
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8"></TableHead>
                <TableHead className="w-[140px]">时间</TableHead>
                <TableHead className="w-[80px]">模型</TableHead>
                <TableHead className="w-[100px]">来源</TableHead>
                <TableHead>问题</TableHead>
                <TableHead className="max-w-[300px]">回答</TableHead>
                <TableHead className="w-[100px]">信息源</TableHead>
                <TableHead className="w-[60px]">详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredResults.map((r) => {
                const isExpanded = expandedId === r.id;
                const sourcesArr = Array.isArray(r.sources) ? r.sources : [];
                const aiCount = Array.isArray(r.ai_read_sources) ? r.ai_read_sources.length : 0;
                const pt = r.provider_type || "api";

                return (
                  <>
                    <TableRow
                      key={r.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleExpand(r.id)}
                    >
                      <TableCell className="px-2">
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleString("zh-CN")}</TableCell>
                      <TableCell><Badge variant="outline">{r.model_name || "-"}</Badge></TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Badge variant="outline" className={pt.startsWith("browser_") ? "bg-blue-50 text-blue-700 border-blue-300" : ""}>
                            {providerLabels[pt] || pt}
                          </Badge>
                          {pt.startsWith("browser_") && (
                            <Badge variant="secondary" className="text-xs">
                              {sourceTypeLabels[r.source_type] || r.source_type}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell><div className="max-w-[200px] truncate">{r.question_text}</div></TableCell>
                      <TableCell><div className="max-w-[300px] truncate">{r.answer_text}</div></TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Badge variant="secondary">{sourcesArr.length} 条</Badge>
                          {aiCount > 0 && (
                            <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-300">
                              AI阅读 {aiCount}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => { e.stopPropagation(); openDetail(r); }}
                        >
                          <FileText className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>

                    {/* Inline expand row: answer preview + source links */}
                    {isExpanded && (
                      <TableRow key={`${r.id}-expand`}>
                        <TableCell colSpan={8} className="bg-muted/30 p-4">
                          <div className="space-y-3">
                            {/* Answer preview */}
                            <div>
                              <p className="text-xs font-medium text-muted-foreground mb-1">回答摘要</p>
                              <p className="text-sm whitespace-pre-wrap">
                                {r.answer_text
                                  ? r.answer_text.length > 200
                                    ? r.answer_text.slice(0, 200) + "..."
                                    : r.answer_text
                                  : "无回答内容"}
                              </p>
                            </div>

                            {/* Source links preview */}
                            {aiCount > 0 && Array.isArray(r.ai_read_sources) && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground mb-1">AI 阅读来源 ({aiCount})</p>
                                <div className="flex flex-wrap gap-2">
                                  {r.ai_read_sources.slice(0, 5).map((url, i) => (
                                    <a
                                      key={i}
                                      href={url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline bg-blue-50 rounded px-2 py-0.5"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink className="h-3 w-3 shrink-0" />
                                      {getDomain(url)}
                                    </a>
                                  ))}
                                  {aiCount > 5 && <span className="text-xs text-muted-foreground">+{aiCount - 5} 更多</span>}
                                </div>
                              </div>
                            )}

                            {/* Crawled pages summary */}
                            {expandCrawledLoading ? (
                              <Skeleton className="h-6 w-48" />
                            ) : expandCrawled.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground mb-1">
                                  已爬取 {expandCrawled.length} 个页面
                                  {" "}({expandCrawled.filter((p) => p.crawl_success).length} 成功)
                                </p>
                              </div>
                            )}

                            <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openDetail(r); }}>
                              查看完整详情
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!detailResult} onOpenChange={(open) => { if (!open) setDetailResult(null); }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          {detailResult && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  问答详情
                </DialogTitle>
              </DialogHeader>

              <Tabs defaultValue="answer" className="mt-4">
                <TabsList>
                  <TabsTrigger value="answer">回答内容</TabsTrigger>
                  <TabsTrigger value="sources">
                    信息源 ({Array.isArray(detailResult.sources) ? detailResult.sources.length : 0})
                  </TabsTrigger>
                  <TabsTrigger value="crawled">
                    爬取内容 ({crawledPages.length})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="answer" className="space-y-3 mt-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">问题</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">{detailResult.question_text}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium text-muted-foreground">AI 回答</CardTitle>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {detailResult.response_time_ms > 0 ? `${(detailResult.response_time_ms / 1000).toFixed(1)}s` : "-"}
                          <Badge variant="outline" className="text-xs">{detailResult.model_name || detailResult.provider_type}</Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <FormattedAnswer text={detailResult.answer_text} />
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="sources" className="mt-4">
                  {Array.isArray(detailResult.ai_read_sources) && detailResult.ai_read_sources.length > 0 && (
                    <Card className="mb-3">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Globe className="h-4 w-4 text-green-600" />
                          AI 阅读的网页 ({detailResult.ai_read_sources.length})
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1">
                          {detailResult.ai_read_sources.map((url, i) => (
                            <a
                              key={i}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 text-sm text-blue-600 hover:underline truncate"
                            >
                              <ExternalLink className="h-3 w-3 shrink-0" />
                              {url}
                            </a>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">解析到的信息源</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {Array.isArray(detailResult.sources) && detailResult.sources.length > 0 ? (
                        <div className="space-y-3">
                          {(detailResult.sources as Array<{ url?: string; title?: string; text_snippet?: string }>).map((s, i) => (
                            <div key={i} className="border rounded-lg p-3 space-y-1">
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-sm font-semibold">{s.title || (s.url ? getDomain(s.url) : "无标题")}</p>
                                <Badge variant="outline" className="text-xs shrink-0">#{i + 1}</Badge>
                              </div>
                              {s.url && (
                                <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-600 hover:underline truncate">
                                  <ExternalLink className="h-3 w-3 shrink-0" />
                                  {s.url}
                                </a>
                              )}
                              {s.text_snippet && (
                                <p className="text-xs text-muted-foreground line-clamp-3 mt-1">{s.text_snippet}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">无解析到的信息源</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="crawled" className="mt-4">
                  {crawledLoading ? (
                    <div className="space-y-3">
                      <Skeleton className="h-32 w-full" />
                      <Skeleton className="h-32 w-full" />
                    </div>
                  ) : crawledPages.length === 0 ? (
                    <Card>
                      <CardContent className="py-8 text-center text-muted-foreground">
                        暂无爬取的网页内容
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="space-y-3">
                      {crawledPages.map((page, i) => (
                        <Card key={page.id} className={!page.crawl_success ? "border-red-200" : ""}>
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <CardTitle className="text-sm font-semibold truncate">
                                  {page.title || getDomain(page.url)}
                                </CardTitle>
                                <a
                                  href={page.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-600 hover:underline truncate mt-1"
                                >
                                  <ExternalLink className="h-3 w-3 shrink-0" />
                                  {page.url}
                                </a>
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                {page.crawl_success ? (
                                  <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-300">
                                    {page.word_count} 词
                                  </Badge>
                                ) : (
                                  <Badge variant="destructive" className="text-xs">爬取失败</Badge>
                                )}
                                <Badge variant="secondary" className="text-xs">#{i + 1}</Badge>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            {page.crawl_success ? (
                              <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-sans leading-relaxed max-h-[300px] overflow-y-auto bg-muted/30 rounded p-3">
                                {page.text_content ? (page.text_content.length > 3000 ? page.text_content.slice(0, 3000) + "\n\n... (内容已截断)" : page.text_content) : "无文本内容"}
                              </pre>
                            ) : (
                              <p className="text-sm text-red-600">{page.crawl_error || "未知错误"}</p>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
