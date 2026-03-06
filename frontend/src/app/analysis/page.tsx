"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import * as echarts from "echarts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Eye, TrendingUp, MessageSquare, Swords, Download, Activity } from "lucide-react";
import { toast } from "sonner";
import { brandApi, analysisApi } from "@/lib/api";
import type { Brand } from "@/types";

interface AnalysisData {
  brand_name: string;
  total_results: number;
  visibility: { score: number; mentioned_count: number; total: number };
  ranking: { avg_position: number; positions: number[] };
  sentiment: { positive: number; neutral: number; negative: number };
  sources: { domains: { domain: string; count: number; percentage: number }[]; total_sources: number };
  trend: { date: string; visibility: number; total: number; mentioned: number }[];
}

function useChart(renderFn: (chart: echarts.ECharts) => void, deps: unknown[]) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(ref.current);
    }
    renderFn(chartRef.current);

    const handleResize = () => chartRef.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}

interface CompetitorItem {
  brand_id: string;
  brand_name: string;
  visibility: number;
  avg_position: number;
  sentiment_positive: number;
  sentiment_negative: number;
  total_results: number;
}

export default function AnalysisPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const [days, setDays] = useState("30");
  const [data, setData] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [competitorData, setCompetitorData] = useState<CompetitorItem[]>([]);
  const [competitorLoading, setCompetitorLoading] = useState(false);

  useEffect(() => {
    brandApi.list().then((res) => setBrands(res.data)).catch(() => {});
  }, []);

  const fetchAnalysis = useCallback(async () => {
    if (!selectedBrandId) return;
    setLoading(true);
    try {
      const res = await analysisApi.brand(selectedBrandId, parseInt(days));
      setData(res.data);
    } catch {
      toast.error("加载分析数据失败");
    } finally {
      setLoading(false);
    }
  }, [selectedBrandId, days]);

  useEffect(() => { fetchAnalysis(); }, [fetchAnalysis]);

  // Fetch competitor data when we have 2+ brands
  const fetchCompetitor = useCallback(async () => {
    if (brands.length < 2) return;
    setCompetitorLoading(true);
    try {
      const ids = brands.map((b) => b.id);
      const res = await analysisApi.competitor(ids);
      setCompetitorData(res.data);
    } catch {
      setCompetitorData([]);
    } finally {
      setCompetitorLoading(false);
    }
  }, [brands]);

  useEffect(() => { fetchCompetitor(); }, [fetchCompetitor]);

  // --- Charts ---
  const visibilityRef = useChart((chart) => {
    if (!data?.trend?.length) { chart.clear(); return; }
    chart.setOption({
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: data.trend.map((t) => t.date) },
      yAxis: { type: "value", max: 100, axisLabel: { formatter: "{value}%" } },
      series: [{ name: "可见性", type: "line", data: data.trend.map((t) => t.visibility), smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: "#3b82f6" } }],
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
    });
  }, [data?.trend]);

  const sentimentRef = useChart((chart) => {
    if (!data) { chart.clear(); return; }
    const { positive, neutral, negative } = data.sentiment;
    chart.setOption({
      tooltip: { trigger: "item" },
      series: [{
        type: "pie", radius: ["40%", "70%"],
        data: [
          { value: positive, name: "正面", itemStyle: { color: "#22c55e" } },
          { value: neutral, name: "中性", itemStyle: { color: "#94a3b8" } },
          { value: negative, name: "负面", itemStyle: { color: "#ef4444" } },
        ],
        label: { formatter: "{b}: {d}%" },
      }],
    });
  }, [data?.sentiment]);

  const sourceRef = useChart((chart) => {
    if (!data?.sources?.domains?.length) { chart.clear(); return; }
    const domains = data.sources.domains.slice(0, 8);
    chart.setOption({
      tooltip: { trigger: "axis" },
      xAxis: { type: "value" },
      yAxis: { type: "category", data: domains.map((d) => d.domain).reverse(), axisLabel: { width: 120, overflow: "truncate" } },
      series: [{ type: "bar", data: domains.map((d) => d.count).reverse(), itemStyle: { color: "#6366f1" } }],
      grid: { left: 140, right: 20, top: 10, bottom: 30 },
    });
  }, [data?.sources]);

  const competitorRef = useChart((chart) => {
    if (!competitorData.length) { chart.clear(); return; }
    const names = competitorData.map((c) => c.brand_name);
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["可见性", "正面情感", "总结果数"] },
      xAxis: { type: "category", data: names },
      yAxis: [
        { type: "value", name: "百分比", max: 100, axisLabel: { formatter: "{value}%" } },
        { type: "value", name: "数量" },
      ],
      series: [
        { name: "可见性", type: "bar", data: competitorData.map((c) => c.visibility), itemStyle: { color: "#3b82f6" } },
        { name: "正面情感", type: "bar", data: competitorData.map((c) => c.total_results > 0 ? Math.round(c.sentiment_positive / c.total_results * 100) : 0), itemStyle: { color: "#22c55e" } },
        { name: "总结果数", type: "line", yAxisIndex: 1, data: competitorData.map((c) => c.total_results), itemStyle: { color: "#f59e0b" } },
      ],
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
    });
  }, [competitorData]);

  const hasData = data && data.total_results > 0;
  const sentimentTotal = data ? data.sentiment.positive + data.sentiment.neutral + data.sentiment.negative : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">分析解读</h1>
          <p className="text-sm text-muted-foreground">品牌 GEO 可见性分析与竞品对比</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedBrandId} onValueChange={setSelectedBrandId}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="选择品牌" />
            </SelectTrigger>
            <SelectContent>
              {brands.length === 0
                ? <SelectItem value="none" disabled>暂无品牌</SelectItem>
                : brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="时间范围" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">近7天</SelectItem>
              <SelectItem value="30">近30天</SelectItem>
              <SelectItem value="90">近90天</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasData}
            onClick={() => {
              if (!data) return;
              const lines = [
                `品牌分析报告: ${data.brand_name}`,
                `时间范围: 近${days}天`,
                "",
                `可见性: ${data.visibility.score}% (${data.visibility.mentioned_count}/${data.visibility.total})`,
                `平均排名: ${data.ranking.avg_position || "N/A"}`,
                `情感: 正面${data.sentiment.positive} / 中性${data.sentiment.neutral} / 负面${data.sentiment.negative}`,
                `信息源总数: ${data.sources.total_sources}`,
                "",
                "信源分布:",
                ...data.sources.domains.map((d) => `  ${d.domain}: ${d.count} (${d.percentage}%)`),
                "",
                "趋势数据:",
                "日期,可见性%,总数,提及数",
                ...data.trend.map((t) => `${t.date},${t.visibility},${t.total},${t.mentioned}`),
              ];
              const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${data.brand_name}_GEO分析报告.txt`;
              a.click();
              window.URL.revokeObjectURL(url);
              toast.success("报告导出成功");
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            导出报告
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">品牌可见性</CardTitle>
              <Eye className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{hasData ? `${data.visibility.score}%` : "--%"}</div>
              <Progress value={hasData ? data.visibility.score : 0} className="mt-2" />
              {hasData && <p className="text-xs text-muted-foreground mt-1">{data.visibility.mentioned_count}/{data.visibility.total} 条提及</p>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">排名水平</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{hasData && data.ranking.avg_position > 0 ? `#${data.ranking.avg_position}` : "--"}</div>
              <p className="text-xs text-muted-foreground mt-1">平均排名位置</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">情感倾向</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {hasData && sentimentTotal > 0 ? (
                <>
                  <div className="text-2xl font-bold">{Math.round(data.sentiment.positive / sentimentTotal * 100)}% 正面</div>
                  <p className="text-xs text-muted-foreground mt-1">{data.sentiment.positive} 正 / {data.sentiment.neutral} 中 / {data.sentiment.negative} 负</p>
                </>
              ) : (
                <div className="text-2xl font-bold">--</div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Analysis Tabs */}
      <Tabs defaultValue="visibility" className="space-y-4">
        <TabsList>
          <TabsTrigger value="visibility"><Eye className="mr-1 h-3.5 w-3.5" />品牌可见性</TabsTrigger>
          <TabsTrigger value="sentiment"><MessageSquare className="mr-1 h-3.5 w-3.5" />情感分析</TabsTrigger>
          <TabsTrigger value="competitor"><Swords className="mr-1 h-3.5 w-3.5" />竞品分析</TabsTrigger>
        </TabsList>

        <TabsContent value="visibility">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">品牌可见性趋势</CardTitle>
              <CardDescription>品牌在 AI 搜索结果中的可见性变化</CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedBrandId ? (
                <Placeholder text="请选择品牌查看分析" />
              ) : loading ? (
                <Skeleton className="h-[250px]" />
              ) : hasData && data.trend.length > 0 ? (
                <div ref={visibilityRef} className="h-[250px]" />
              ) : (
                <Placeholder text="暂无趋势数据" />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sentiment">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">情感分析</CardTitle>
              <CardDescription>品牌在 AI 回答中的情感倾向分布</CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedBrandId ? (
                <Placeholder text="请选择品牌查看分析" />
              ) : loading ? (
                <Skeleton className="h-[250px]" />
              ) : hasData && sentimentTotal > 0 ? (
                <div ref={sentimentRef} className="h-[250px]" />
              ) : (
                <Placeholder text="暂无情感数据" />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="competitor">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">竞品分析</CardTitle>
              <CardDescription>品牌与竞品的 GEO 表现对比（需要至少2个品牌有完成的任务）</CardDescription>
            </CardHeader>
            <CardContent>
              {competitorLoading ? (
                <Skeleton className="h-[250px]" />
              ) : competitorData.length >= 2 ? (
                <div ref={competitorRef} className="h-[250px]" />
              ) : (
                <Placeholder text={brands.length < 2 ? "需要创建至少2个品牌" : "暂无足够的竞品数据"} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Source Analysis */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">信源分析</CardTitle>
            <CardDescription>AI 引用的信息源分布</CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedBrandId ? (
              <Placeholder text="请选择品牌" small />
            ) : loading ? (
              <Skeleton className="h-[200px]" />
            ) : hasData && data.sources.domains.length > 0 ? (
              <div ref={sourceRef} className="h-[200px]" />
            ) : (
              <Placeholder text="暂无信源数据" small />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">数据概览</CardTitle>
            <CardDescription>当前分析数据统计</CardDescription>
          </CardHeader>
          <CardContent>
            {hasData ? (
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-muted-foreground">总回答数</span><span className="font-medium">{data.total_results}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">品牌提及数</span><span className="font-medium">{data.visibility.mentioned_count}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">信息源总数</span><span className="font-medium">{data.sources.total_sources}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">涉及域名数</span><span className="font-medium">{data.sources.domains.length}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">趋势数据点</span><span className="font-medium">{data.trend.length} 天</span></div>
              </div>
            ) : (
              <Placeholder text="请选择品牌查看数据概览" small />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Placeholder({ text, small }: { text: string; small?: boolean }) {
  return (
    <div className={`flex ${small ? "h-[200px]" : "h-[250px]"} items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground`}>
      <div className="flex flex-col items-center gap-2">
        <Activity className="h-8 w-8" />
        <span>{text}</span>
      </div>
    </div>
  );
}
