"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Plus, Search, Play, Pause, Eye } from "lucide-react";

export default function TasksPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("all");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">任务管理</h1>
          <p className="text-sm text-muted-foreground">创建和管理 GEO 监测任务</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              创建任务
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>创建任务</DialogTitle>
              <DialogDescription>配置任务参数并开始监测</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="task-name">任务名称</Label>
                <Input id="task-name" placeholder="请输入任务名称" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>选择品牌</Label>
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
                  <Label>选择问题集</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="选择问题集" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">暂无问题集</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <Label>模型场景</Label>
                <RadioGroup defaultValue="pc" className="flex gap-4">
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="mobile" id="mobile" />
                    <Label htmlFor="mobile" className="font-normal">手机模拟</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="pc" id="pc" />
                    <Label htmlFor="pc" className="font-normal">PC模式</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="api" id="api" />
                    <Label htmlFor="api" className="font-normal">API调用</Label>
                  </div>
                </RadioGroup>
              </div>
              <div className="grid gap-2">
                <Label>任务类型</Label>
                <RadioGroup defaultValue="once" className="flex gap-4">
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="once" id="once" />
                    <Label htmlFor="once" className="font-normal">单次任务</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="recurring" id="recurring" />
                    <Label htmlFor="recurring" className="font-normal">循环任务</Label>
                  </div>
                </RadioGroup>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="ip-switch">切换IP</Label>
                  <Switch id="ip-switch" />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="privacy">隐私模式</Label>
                  <Switch id="privacy" />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="rounds">提问轮次</Label>
                <div className="flex items-center gap-2">
                  <Input id="rounds" type="number" defaultValue={1} className="w-20" />
                  <span className="text-sm text-muted-foreground">轮</span>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={() => setDialogOpen(false)}>创建任务</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader className="pb-3">
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
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="搜索任务..." className="pl-9" />
            </div>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务名称</TableHead>
                <TableHead>品牌</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>进度</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="w-32 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                  暂无任务，点击右上角"创建任务"开始
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
