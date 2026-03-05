"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { BarChart3, TrendingUp, Eye, MessageSquare, Swords, Download } from "lucide-react";

export default function AnalysisPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">分析解读</h1>
          <p className="text-sm text-muted-foreground">品牌 GEO 可见性分析与竞品对比</p>
        </div>
        <div className="flex items-center gap-3">
          <Select>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="选择品牌" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">暂无品牌</SelectItem>
            </SelectContent>
          </Select>
          <Select>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="时间范围" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">近7天</SelectItem>
              <SelectItem value="30d">近30天</SelectItem>
              <SelectItem value="90d">近90天</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            导出报告
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>品牌可见性</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">--%</div>
            <Progress value={0} className="mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>排名水平</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">--</div>
            <p className="text-xs text-muted-foreground mt-1">平均排名位置</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>情感倾向</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">--</div>
            <p className="text-xs text-muted-foreground mt-1">正面/中性/负面</p>
          </CardContent>
        </Card>
      </div>

      {/* Analysis Tabs */}
      <Tabs defaultValue="visibility" className="space-y-4">
        <TabsList>
          <TabsTrigger value="visibility">
            <Eye className="mr-1 h-3.5 w-3.5" />
            品牌可见性
          </TabsTrigger>
          <TabsTrigger value="ranking">
            <TrendingUp className="mr-1 h-3.5 w-3.5" />
            排名水平
          </TabsTrigger>
          <TabsTrigger value="sentiment">
            <MessageSquare className="mr-1 h-3.5 w-3.5" />
            情感分析
          </TabsTrigger>
          <TabsTrigger value="competitor">
            <Swords className="mr-1 h-3.5 w-3.5" />
            竞品分析
          </TabsTrigger>
        </TabsList>

        <TabsContent value="visibility">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">品牌可见性趋势</CardTitle>
              <CardDescription>折线图：品牌在 AI 搜索结果中的可见性变化</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                请选择品牌和时间范围查看分析
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ranking">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">排名水平趋势</CardTitle>
              <CardDescription>折线图：品牌在回答中的排名位置变化</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                请选择品牌和时间范围查看分析
              </div>
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
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                请选择品牌和时间范围查看分析
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="competitor">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">竞品分析</CardTitle>
              <CardDescription>品牌与竞品的 GEO 表现对比</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                请选择品牌和时间范围查看分析
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Source Analysis & Content Suggestions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">信源分析</CardTitle>
            <CardDescription>AI 引用的信息源分布与抓取倾向</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              词云 & 信源统计区域
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">内容生成建议</CardTitle>
            <CardDescription>基于分析结果的内容优化方向和信息源头推荐</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              优化建议列表区域
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
