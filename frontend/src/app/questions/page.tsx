"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Plus, Search, Upload, Sparkles, Trash2 } from "lucide-react";

export default function QuestionsPage() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">问题管理</h1>
          <p className="text-sm text-muted-foreground">管理品牌问题集和问题内容</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                新建问题集
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>新建问题集</DialogTitle>
                <DialogDescription>为品牌创建新的问题集</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label>关联品牌</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="选择品牌" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">暂无品牌</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="set-name">问题集名称</Label>
                  <Input id="set-name" placeholder="请输入问题集名称" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="set-desc">描述</Label>
                  <Textarea id="set-desc" placeholder="问题集描述（可选）" rows={2} />
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
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="搜索问题集..." className="pl-9" />
            </div>
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="所有品牌" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">所有品牌</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>问题集名称</TableHead>
                <TableHead>关联品牌</TableHead>
                <TableHead>问题数</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="w-32 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  暂无问题集
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">问题录入</h3>
            <Tabs defaultValue="manual" className="w-auto">
              <TabsList>
                <TabsTrigger value="manual">
                  <Plus className="mr-1 h-3 w-3" />
                  单条录入
                </TabsTrigger>
                <TabsTrigger value="batch">
                  <Upload className="mr-1 h-3 w-3" />
                  批量上传
                </TabsTrigger>
                <TabsTrigger value="ai">
                  <Sparkles className="mr-1 h-3 w-3" />
                  智能生成
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="pt-4">
          <div className="text-center text-sm text-muted-foreground py-8">
            请先选择一个问题集，再进行问题录入
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
