"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Search, Download, Eye, ExternalLink } from "lucide-react";

export default function QADetailPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">问答明细</h1>
          <p className="text-sm text-muted-foreground">查看任务的问答回收结果和信息源</p>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          导出数据
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center gap-3">
            <Select>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="选择任务" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">暂无任务</SelectItem>
              </SelectContent>
            </Select>
            <Select>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="模型筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部模型</SelectItem>
              </SelectContent>
            </Select>
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="搜索问题或回答..." className="pl-9" />
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Data table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">#</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>版本</TableHead>
                <TableHead className="max-w-[200px]">问题</TableHead>
                <TableHead className="max-w-[300px]">回答</TableHead>
                <TableHead>信息源</TableHead>
                <TableHead className="w-20 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={8} className="h-48 text-center text-muted-foreground">
                  请选择任务查看问答明细
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
