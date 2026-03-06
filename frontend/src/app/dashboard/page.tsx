"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Building2, HelpCircle, ListTodo, CheckCircle, Activity, ArrowRight, Clock, AlertCircle } from "lucide-react";
import { statsApi, type DashboardStats, taskApi, brandApi } from "@/lib/api";
import type { Task, Brand } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
  pending: "bg-yellow-500",
  paused: "bg-orange-500",
};

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      statsApi.dashboard().then((res) => setStats(res.data)).catch(() => setStats({ brand_count: 0, question_set_count: 0, running_tasks: 0, completed_tasks: 0, total_tasks: 0 })),
      taskApi.list({ page_size: 5 }).then((res) => setRecentTasks(res.data)).catch(() => {}),
      brandApi.list({ page_size: 5 }).then((res) => setBrands(res.data)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const cards = [
    { label: "品牌数", value: stats?.brand_count ?? 0, desc: "已创建品牌", icon: Building2 },
    { label: "问题集数", value: stats?.question_set_count ?? 0, desc: "已创建问题集", icon: HelpCircle },
    { label: "进行中任务", value: stats?.running_tasks ?? 0, desc: "当前运行任务", icon: ListTodo },
    { label: "已完成任务", value: stats?.completed_tasks ?? 0, desc: "累计完成任务", icon: CheckCircle },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">概览</h1>
        <p className="text-sm text-muted-foreground">欢迎使用灵渡GEO系统</p>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="analytics">快速入口</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {cards.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.label}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">{stat.label}</CardTitle>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    {loading ? (
                      <Skeleton className="h-8 w-16" />
                    ) : (
                      <div className="text-2xl font-bold">{stat.value}</div>
                    )}
                    <p className="text-xs text-muted-foreground">{stat.desc}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <Card className="col-span-4">
              <CardHeader>
                <CardTitle>最近任务</CardTitle>
                <CardDescription>最近创建的监测任务</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}
                  </div>
                ) : recentTasks.length === 0 ? (
                  <div className="flex h-[200px] items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <Activity className="h-8 w-8" />
                      <span>暂无任务，前往任务管理创建</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentTasks.map((task) => (
                      <div key={task.id} className="flex items-center gap-3 rounded-lg border p-3">
                        <div className={`h-2 w-2 rounded-full ${STATUS_COLORS[task.status] || "bg-gray-400"}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{task.name}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant="outline" className="text-[10px] h-4">{task.status}</Badge>
                            {task.status === "running" && <span>{task.progress}%</span>}
                            <span>{new Date(task.created_at).toLocaleDateString("zh-CN")}</span>
                          </div>
                        </div>
                        {task.status === "running" && (
                          <Progress value={task.progress} className="w-20" />
                        )}
                      </div>
                    ))}
                    <Button variant="ghost" size="sm" className="w-full" onClick={() => router.push("/tasks")}>
                      查看全部任务 <ArrowRight className="ml-1 h-3 w-3" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card className="col-span-3">
              <CardHeader>
                <CardTitle>品牌概况</CardTitle>
                <CardDescription>已创建的品牌列表</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="space-y-3">
                    {[1, 2].map((i) => <Skeleton key={i} className="h-10" />)}
                  </div>
                ) : brands.length === 0 ? (
                  <div className="flex h-[200px] items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <Building2 className="h-8 w-8" />
                      <span>暂无品牌</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {brands.map((brand) => (
                      <div key={brand.id} className="flex items-center justify-between rounded-lg border p-3">
                        <div>
                          <p className="text-sm font-medium">{brand.name}</p>
                          <p className="text-xs text-muted-foreground">{brand.industry || "未设置行业"}</p>
                        </div>
                        {brand.price_range && <Badge variant="secondary">{brand.price_range}</Badge>}
                      </div>
                    ))}
                    <Button variant="ghost" size="sm" className="w-full" onClick={() => router.push("/brands")}>
                      管理品牌 <ArrowRight className="ml-1 h-3 w-3" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push("/brands")}>
              <CardHeader>
                <Building2 className="h-8 w-8 text-blue-500" />
                <CardTitle className="text-base">品牌管理</CardTitle>
                <CardDescription>创建和管理监测品牌</CardDescription>
              </CardHeader>
            </Card>
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push("/tasks")}>
              <CardHeader>
                <ListTodo className="h-8 w-8 text-green-500" />
                <CardTitle className="text-base">任务管理</CardTitle>
                <CardDescription>创建和执行监测任务</CardDescription>
              </CardHeader>
            </Card>
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push("/analysis")}>
              <CardHeader>
                <Activity className="h-8 w-8 text-purple-500" />
                <CardTitle className="text-base">分析解读</CardTitle>
                <CardDescription>查看品牌GEO分析报告</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
