"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";

export default function BrandsPage() {
  const [searchKeyword, setSearchKeyword] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">品牌管理</h1>
          <p className="text-sm text-muted-foreground">管理您的品牌信息和相关配置</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              新建品牌
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>新建品牌</DialogTitle>
              <DialogDescription>填写品牌基础信息，创建后可继续编辑详细内容</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="brand-name">品牌名称</Label>
                <Input id="brand-name" placeholder="请输入品牌名称" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="brand-industry">行业</Label>
                <Input id="brand-industry" placeholder="请输入行业" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="brand-audience">目标用户群</Label>
                  <Input id="brand-audience" placeholder="目标用户" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="brand-price">价格区间</Label>
                  <Input id="brand-price" placeholder="价格区间" />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="brand-selling">卖点</Label>
                <Textarea id="brand-selling" placeholder="品牌核心卖点" rows={3} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={() => setDialogOpen(false)}>确认创建</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader className="pb-3">
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
            <Badge variant="secondary">共 0 个品牌</Badge>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>品牌名称</TableHead>
                <TableHead>行业</TableHead>
                <TableHead>用户群</TableHead>
                <TableHead>卖点</TableHead>
                <TableHead>价格</TableHead>
                <TableHead className="w-24 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  暂无品牌数据，点击右上角"新建品牌"开始
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
