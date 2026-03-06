"use client";

import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { DataTable } from "@/components/data-table";
import { Plus, Search, Play, Pause, Trash2 } from "lucide-react";
import { brandApi, questionSetApi, taskApi } from "@/lib/api";
import type { Brand, QuestionSet, Task } from "@/types";

const taskSchema = z.object({
  name: z.string().min(1, "任务名称不能为空"),
  brand_id: z.string().min(1, "请选择品牌"),
  question_set_id: z.string().min(1, "请选择问题集"),
  model_scene: z.string(),
  task_type: z.string(),
});
type TaskFormValues = z.infer<typeof taskSchema>;

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "待开始", variant: "outline" },
  running: { label: "运行中", variant: "default" },
  completed: { label: "已完成", variant: "secondary" },
  failed: { label: "已失败", variant: "destructive" },
  paused: { label: "已暂停", variant: "outline" },
};

export default function TasksPage() {
  const [data, setData] = useState<Task[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("all");

  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskSchema),
    defaultValues: { name: "", brand_id: "", question_set_id: "", model_scene: "pc", task_type: "once" },
  });

  const selectedBrandId = form.watch("brand_id");

  const fetchData = useCallback(async () => {
    try {
      const [taskRes, brandRes] = await Promise.all([
        taskApi.list({ task_status: activeTab === "all" ? undefined : activeTab }),
        brandApi.list(),
      ]);
      setData(taskRes.data);
      setBrands(brandRes.data);
    } catch {
      toast.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Load question sets when brand changes in form
  useEffect(() => {
    if (selectedBrandId) {
      questionSetApi.list({ brand_id: selectedBrandId }).then((res) => setQuestionSets(res.data)).catch(() => {});
    } else {
      setQuestionSets([]);
    }
  }, [selectedBrandId]);

  const onSubmit = async (values: TaskFormValues) => {
    try {
      await taskApi.create(values);
      toast.success("任务创建成功");
      setDialogOpen(false);
      form.reset();
      fetchData();
    } catch {
      toast.error("创建失败");
    }
  };

  const handleStart = async (id: string) => {
    try { await taskApi.start(id); toast.success("任务已启动"); fetchData(); }
    catch { toast.error("启动失败"); }
  };

  const handlePause = async (id: string) => {
    try { await taskApi.pause(id); toast.success("任务已暂停"); fetchData(); }
    catch { toast.error("暂停失败"); }
  };

  const handleDelete = async (id: string) => {
    try { await taskApi.delete(id); toast.success("任务已删除"); fetchData(); }
    catch { toast.error("删除失败"); }
  };

  const brandNameMap = Object.fromEntries(brands.map((b) => [b.id, b.name]));

  const columns: ColumnDef<Task>[] = [
    { accessorKey: "name", header: "任务名称" },
    { accessorKey: "brand_id", header: "品牌", cell: ({ row }) => brandNameMap[row.getValue("brand_id") as string] || "-" },
    { accessorKey: "task_type", header: "类型", cell: ({ row }) => row.getValue("task_type") === "once" ? "单次" : "循环" },
    {
      accessorKey: "status", header: "状态",
      cell: ({ row }) => {
        const s = statusMap[row.getValue("status") as string] || { label: row.getValue("status"), variant: "outline" as const };
        return <Badge variant={s.variant}>{s.label}</Badge>;
      },
    },
    { accessorKey: "progress", header: "进度", cell: ({ row }) => <div className="w-24"><Progress value={row.getValue("progress") as number} className="h-2" /></div> },
    { accessorKey: "created_at", header: "创建时间", cell: ({ row }) => new Date(row.getValue("created_at") as string).toLocaleDateString("zh-CN") },
    {
      id: "actions",
      header: () => <div className="text-right">操作</div>,
      cell: ({ row }) => {
        const task = row.original;
        return (
          <div className="flex justify-end gap-1">
            {(task.status === "pending" || task.status === "paused") && (
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleStart(task.id)}>
                <Play className="h-3.5 w-3.5" />
              </Button>
            )}
            {task.status === "running" && (
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handlePause(task.id)}>
                <Pause className="h-3.5 w-3.5" />
              </Button>
            )}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"><Trash2 className="h-3.5 w-3.5" /></Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader><AlertDialogTitle>确认删除</AlertDialogTitle><AlertDialogDescription>确定要删除任务「{task.name}」吗？此操作不可撤销。</AlertDialogDescription></AlertDialogHeader>
                <AlertDialogFooter><AlertDialogCancel>取消</AlertDialogCancel><AlertDialogAction onClick={() => handleDelete(task.id)}>删除</AlertDialogAction></AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        );
      },
    },
  ];

  if (loading) {
    return <div className="space-y-4"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">任务管理</h1>
          <p className="text-sm text-muted-foreground">创建和管理 GEO 监测任务</p>
        </div>
        <Button onClick={() => { form.reset(); setDialogOpen(true); }}>
          <Plus className="mr-2 h-4 w-4" />
          创建任务
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="all">全部</TabsTrigger>
            <TabsTrigger value="pending">待开始</TabsTrigger>
            <TabsTrigger value="running">运行中</TabsTrigger>
            <TabsTrigger value="completed">已完成</TabsTrigger>
            <TabsTrigger value="failed">已失败</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <DataTable columns={columns} data={data} emptyMessage="暂无任务，点击右上角「创建任务」开始" />

      <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) form.reset(); }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>创建任务</DialogTitle>
            <DialogDescription>配置任务参数并开始监测</DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField control={form.control} name="name" render={({ field }) => (
                <FormItem><FormLabel>任务名称</FormLabel><FormControl><Input placeholder="请输入任务名称" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="brand_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>选择品牌</FormLabel>
                    <Select onValueChange={(v) => { field.onChange(v); form.setValue("question_set_id", ""); }} value={field.value}>
                      <FormControl><SelectTrigger><SelectValue placeholder="选择品牌" /></SelectTrigger></FormControl>
                      <SelectContent>
                        {brands.length === 0 ? <SelectItem value="none" disabled>请先创建品牌</SelectItem>
                          : brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="question_set_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>选择问题集</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl><SelectTrigger><SelectValue placeholder="选择问题集" /></SelectTrigger></FormControl>
                      <SelectContent>
                        {questionSets.length === 0 ? <SelectItem value="none" disabled>请先创建问题集</SelectItem>
                          : questionSets.map((qs) => <SelectItem key={qs.id} value={qs.id}>{qs.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
              <FormField control={form.control} name="model_scene" render={({ field }) => (
                <FormItem>
                  <FormLabel>模型场景</FormLabel>
                  <FormControl>
                    <RadioGroup onValueChange={field.onChange} value={field.value} className="flex gap-4">
                      <div className="flex items-center space-x-2"><RadioGroupItem value="mobile" id="mobile" /><Label htmlFor="mobile" className="font-normal">手机模拟</Label></div>
                      <div className="flex items-center space-x-2"><RadioGroupItem value="pc" id="pc" /><Label htmlFor="pc" className="font-normal">PC模式</Label></div>
                      <div className="flex items-center space-x-2"><RadioGroupItem value="api" id="api" /><Label htmlFor="api" className="font-normal">API调用</Label></div>
                    </RadioGroup>
                  </FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="task_type" render={({ field }) => (
                <FormItem>
                  <FormLabel>任务类型</FormLabel>
                  <FormControl>
                    <RadioGroup onValueChange={field.onChange} value={field.value} className="flex gap-4">
                      <div className="flex items-center space-x-2"><RadioGroupItem value="once" id="once" /><Label htmlFor="once" className="font-normal">单次任务</Label></div>
                      <div className="flex items-center space-x-2"><RadioGroupItem value="recurring" id="recurring" /><Label htmlFor="recurring" className="font-normal">循环任务</Label></div>
                    </RadioGroup>
                  </FormControl>
                </FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
                <Button type="submit">创建任务</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
