# Claude Code × shadcn/ui 提示词模板

以下是在 Claude Code 中使用的提示词模板，直接复制粘贴即可。

---

## 🔄 迁移现有页面到 shadcn/ui

```
将 [文件路径] 中的 UI 迁移到 shadcn/ui 组件。

步骤：
1. 分析当前页面用了哪些 HTML 元素和自定义组件
2. 确定需要安装哪些 shadcn/ui 组件
3. 运行 `npx shadcn@latest add [组件名]` 安装缺失组件
4. 将所有原生 HTML 替换为对应的 shadcn/ui 组件：
   - <button> → <Button>
   - <input> → <Input>
   - <table> → <Table> + <TableHeader> + <TableBody> + <TableRow> + <TableCell>
   - 自定义 modal → <Dialog>
   - 自定义 sidebar → <Sheet>
   - 自定义 card → <Card> + <CardHeader> + <CardContent>
5. 使用 shadcn 的 CSS 变量颜色 (bg-primary, text-muted-foreground 等)
6. 确保交互组件有 "use client" 指令
7. 保持所有现有逻辑和功能不变
```

---

## 🆕 新建页面（直接使用 shadcn/ui）

```
创建 [页面路径] 页面，使用 shadcn/ui 组件构建。

页面功能：[描述页面功能]

要求：
- 先安装所有需要的 shadcn/ui 组件 (npx shadcn@latest add xxx)
- 使用 shadcn/ui Card 做数据卡片
- 使用 shadcn/ui Table 做数据表格
- 使用 shadcn/ui Dialog 做弹窗
- 使用 shadcn/ui Select/Input 做表单
- 使用 lucide-react 图标
- 颜色使用 CSS 变量 (bg-background, text-foreground, bg-primary 等)
- 支持 dark mode
- 响应式设计
```

---

## 🩺 诊断 & 修复样式问题

```
我的 shadcn/ui 组件样式不生效，请帮我排查：

1. 检查 components.json 配置是否正确
2. 检查 app/globals.css 是否包含所有 CSS 变量 (--background, --foreground, --primary 等)
3. 检查 app/layout.tsx 是否导入了 globals.css
4. 检查 lib/utils.ts 是否包含 cn() 函数
5. 检查 tailwind 配置的 content 路径是否包含 components/ui 目录
6. 检查组件的依赖包 (class-variance-authority, clsx, tailwind-merge) 是否安装
7. 针对发现的问题给出修复方案并执行
```

---

## 📊 Data Agent 仪表盘专用

```
为数据分析仪表盘创建/更新 [页面路径]，使用 shadcn/ui 组件：

布局结构：
- 顶部：Breadcrumb 导航 + 日期范围选择器 (Calendar + Popover)
- 左侧：Sidebar 导航
- 主区域：
  - 顶部 KPI 卡片行: Card 组件展示 4 个核心指标
  - 中部 Chart 区域: 使用 shadcn Chart (基于 recharts)
  - 下部数据表: DataTable 组件 (shadcn Table + @tanstack/react-table)
    - 支持排序、筛选、分页
- 所有数据使用 Skeleton 做加载状态
- 空数据使用 Empty 状态组件
- 操作确认使用 AlertDialog

先安装所有需要的组件：
npx shadcn@latest add card chart table tabs select calendar popover breadcrumb sidebar skeleton alert-dialog badge button separator
```

---

## 🎨 主题 & 样式自定义

```
更新项目的 shadcn/ui 主题：

1. 在 app/globals.css 中修改 CSS 变量来匹配我的品牌色：
   - primary: [你的品牌色]
   - 确保 light 和 dark 两套变量都更新
2. 调整 border-radius 为 [0.5rem / 0.75rem / 1rem]
3. 确保所有已安装的 shadcn 组件自动继承新主题
```

---

## ⚡ 快速安装常用组件集

```
为项目安装以下 shadcn/ui 组件集并验证安装成功：

基础集: button input label textarea card badge separator skeleton avatar
表单集: checkbox radio-group select switch slider toggle field
弹窗集: dialog alert-dialog sheet drawer popover tooltip
导航集: tabs breadcrumb dropdown-menu navigation-menu pagination sidebar
数据集: table chart progress scroll-area accordion

运行: npx shadcn@latest add [以上所有组件名]

安装后验证：
1. 确认 components/ui 目录下有对应文件
2. 确认 package.json 中有对应的 @radix-ui 依赖
3. 创建一个测试页面展示所有组件
```
