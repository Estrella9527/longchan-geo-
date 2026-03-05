#!/bin/bash
# ============================================================
# shadcn/ui 组件批量安装脚本
# 在项目根目录运行: bash install-shadcn-components.sh
# ============================================================

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " shadcn/ui 组件批量安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查 components.json 是否存在
if [[ ! -f "components.json" ]]; then
  echo "❌ 未检测到 components.json，先初始化 shadcn/ui..."
  npx shadcn@latest init
  echo ""
fi

# ─── 第一批: 最常用基础组件 ───
echo "📦 [1/4] 安装基础组件..."
npx shadcn@latest add \
  button \
  input \
  label \
  textarea \
  card \
  badge \
  separator \
  skeleton \
  spinner \
  avatar \
  -y

# ─── 第二批: 表单相关 ───
echo ""
echo "📦 [2/4] 安装表单组件..."
npx shadcn@latest add \
  checkbox \
  radio-group \
  select \
  switch \
  slider \
  toggle \
  toggle-group \
  input-otp \
  field \
  -y

# ─── 第三批: 弹窗 & 导航 ───
echo ""
echo "📦 [3/4] 安装弹窗和导航组件..."
npx shadcn@latest add \
  dialog \
  alert-dialog \
  sheet \
  drawer \
  dropdown-menu \
  context-menu \
  popover \
  hover-card \
  tooltip \
  command \
  menubar \
  navigation-menu \
  tabs \
  breadcrumb \
  pagination \
  -y

# ─── 第四批: 数据展示 & 高级 ───
echo ""
echo "📦 [4/4] 安装数据展示和高级组件..."
npx shadcn@latest add \
  table \
  alert \
  progress \
  scroll-area \
  collapsible \
  resizable \
  calendar \
  carousel \
  chart \
  sonner \
  toast \
  sidebar \
  accordion \
  aspect-ratio \
  typography \
  empty \
  -y

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ 所有 shadcn/ui 核心组件安装完成!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "已安装的组件:"
ls components/ui/ 2>/dev/null || ls src/components/ui/ 2>/dev/null || echo "请检查 components/ui 目录"
echo ""
echo "下一步:"
echo "  1. 确保 app/globals.css 中有 CSS 变量 (运行 verify-shadcn.sh 检查)"
echo "  2. 将 CLAUDE.md 放入项目根目录"
echo "  3. 将 .mcp.json 放入项目根目录"
echo "  4. 重启 Claude Code"
echo ""
