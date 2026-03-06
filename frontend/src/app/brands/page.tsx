"use client";

import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/data-table";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";
import { brandApi } from "@/lib/api";
import type { Brand } from "@/types";

const brandSchema = z.object({
  name: z.string().min(1, "品牌名称不能为空"),
  industry: z.string().optional(),
  target_audience: z.string().optional(),
  price_range: z.string().optional(),
  selling_points: z.string().optional(),
});
type BrandFormValues = z.infer<typeof brandSchema>;

export default function BrandsPage() {
  const [data, setData] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);

  const form = useForm<BrandFormValues>({
    resolver: zodResolver(brandSchema),
    defaultValues: { name: "", industry: "", target_audience: "", price_range: "", selling_points: "" },
  });

  const fetchBrands = useCallback(async () => {
    try {
      const res = await brandApi.list({ keyword: searchKeyword || undefined });
      setData(res.data);
    } catch {
      toast.error("加载品牌列表失败");
    } finally {
      setLoading(false);
    }
  }, [searchKeyword]);

  useEffect(() => { fetchBrands(); }, [fetchBrands]);

  const openCreate = () => {
    setEditingBrand(null);
    form.reset({ name: "", industry: "", target_audience: "", price_range: "", selling_points: "" });
    setDialogOpen(true);
  };

  const openEdit = (brand: Brand) => {
    setEditingBrand(brand);
    form.reset({
      name: brand.name,
      industry: brand.industry,
      target_audience: brand.target_audience,
      price_range: brand.price_range,
      selling_points: brand.selling_points,
    });
    setDialogOpen(true);
  };

  const onSubmit = async (values: BrandFormValues) => {
    try {
      if (editingBrand) {
        await brandApi.update(editingBrand.id, values);
        toast.success("品牌更新成功");
      } else {
        await brandApi.create({ name: values.name, industry: values.industry, target_audience: values.target_audience, price_range: values.price_range, selling_points: values.selling_points });
        toast.success("品牌创建成功");
      }
      setDialogOpen(false);
      fetchBrands();
    } catch {
      toast.error(editingBrand ? "更新失败" : "创建失败");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await brandApi.delete(id);
      toast.success("品牌已删除");
      fetchBrands();
    } catch {
      toast.error("删除失败");
    }
  };

  const columns: ColumnDef<Brand>[] = [
    { accessorKey: "name", header: "品牌名称" },
    { accessorKey: "industry", header: "行业" },
    { accessorKey: "target_audience", header: "用户群" },
    { accessorKey: "selling_points", header: "卖点", cell: ({ row }) => <div className="max-w-[200px] truncate">{row.getValue("selling_points")}</div> },
    { accessorKey: "price_range", header: "价格" },
    {
      id: "actions",
      header: () => <div className="text-right">操作</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(row.original)}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>确认删除</AlertDialogTitle>
                <AlertDialogDescription>确定要删除品牌「{row.original.name}」吗？此操作不可撤销。</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction onClick={() => handleDelete(row.original.id)}>删除</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-full max-w-sm" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">品牌管理</h1>
          <p className="text-sm text-muted-foreground">管理您的品牌信息和相关配置</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          新建品牌
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索品牌..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary">共 {data.length} 个品牌</Badge>
      </div>

      <DataTable columns={columns} data={data} emptyMessage="暂无品牌数据，点击右上角「新建品牌」开始" />

      <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) form.reset(); }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingBrand ? "编辑品牌" : "新建品牌"}</DialogTitle>
            <DialogDescription>{editingBrand ? "修改品牌信息" : "填写品牌基础信息，创建后可继续编辑详细内容"}</DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField control={form.control} name="name" render={({ field }) => (
                <FormItem><FormLabel>品牌名称</FormLabel><FormControl><Input placeholder="请输入品牌名称" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="industry" render={({ field }) => (
                <FormItem><FormLabel>行业</FormLabel><FormControl><Input placeholder="请输入行业" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="target_audience" render={({ field }) => (
                  <FormItem><FormLabel>目标用户群</FormLabel><FormControl><Input placeholder="目标用户" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="price_range" render={({ field }) => (
                  <FormItem><FormLabel>价格区间</FormLabel><FormControl><Input placeholder="价格区间" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
              </div>
              <FormField control={form.control} name="selling_points" render={({ field }) => (
                <FormItem><FormLabel>卖点</FormLabel><FormControl><Textarea placeholder="品牌核心卖点" rows={3} {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
                <Button type="submit">{editingBrand ? "保存修改" : "确认创建"}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
