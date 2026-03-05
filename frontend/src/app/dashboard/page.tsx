"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Building2, HelpCircle, ListTodo, CheckCircle } from "lucide-react";

const stats = [
  { label: "品牌数", value: "-", icon: Building2, color: "text-blue-500" },
  { label: "问题集数", value: "-", icon: HelpCircle, color: "text-purple-500" },
  { label: "进行中任务", value: "-", icon: ListTodo, color: "text-orange-500" },
  { label: "已完成任务", value: "-", icon: CheckCircle, color: "text-green-500" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">概览</h1>
        <p className="text-sm text-muted-foreground">欢迎使用龙蟾GEO系统</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.label}
                </CardTitle>
                <Icon className={cn("h-4 w-4", stat.color)} />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{stat.value}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
