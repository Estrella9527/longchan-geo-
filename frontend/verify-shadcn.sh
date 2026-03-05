#!/bin/bash
# ============================================================
# shadcn/ui 项目配置检测 & 自动修复脚本
# 用法: bash verify-shadcn.sh [--fix]
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
  FIX_MODE=true
fi

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; ((WARN++)); }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " shadcn/ui 项目配置检测"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ────────────────────────────────────────────────────
# 1. 核心配置文件
# ────────────────────────────────────────────────────
echo "📁 [1/7] 核心配置文件"

if [[ -f "components.json" ]]; then
  pass "components.json 存在"
  
  # 检查 components.json 内容
  if command -v node &> /dev/null; then
    STYLE=$(node -e "try{console.log(JSON.parse(require('fs').readFileSync('components.json','utf8')).style||'未设置')}catch(e){console.log('解析错误')}")
    CSS_PATH=$(node -e "try{console.log(JSON.parse(require('fs').readFileSync('components.json','utf8')).tailwind?.css||'未设置')}catch(e){console.log('解析错误')}")
    ALIASES_UI=$(node -e "try{console.log(JSON.parse(require('fs').readFileSync('components.json','utf8')).aliases?.ui||'未设置')}catch(e){console.log('解析错误')}")
    info "风格: $STYLE | CSS路径: $CSS_PATH | UI别名: $ALIASES_UI"
  fi
else
  fail "components.json 不存在"
  if $FIX_MODE; then
    info "运行 npx shadcn@latest init 来创建..."
    npx shadcn@latest init -y 2>/dev/null || warn "自动init失败，请手动运行 npx shadcn@latest init"
  else
    info "修复: 运行 npx shadcn@latest init"
  fi
fi

# ────────────────────────────────────────────────────
# 2. CSS 变量 (最关键!)
# ────────────────────────────────────────────────────
echo ""
echo "🎨 [2/7] CSS 变量 (样式生效的根基)"

# 查找全局CSS文件
CSS_FILE=""
for f in "app/globals.css" "src/app/globals.css" "styles/globals.css" "src/styles/globals.css"; do
  if [[ -f "$f" ]]; then
    CSS_FILE="$f"
    break
  fi
done

if [[ -z "$CSS_FILE" ]]; then
  fail "找不到全局CSS文件 (globals.css)"
  info "修复: 创建 app/globals.css 并添加 shadcn/ui CSS 变量"
else
  pass "全局CSS文件: $CSS_FILE"
  
  # 检查关键CSS变量
  MISSING_VARS=()
  for var in "--background" "--foreground" "--primary" "--primary-foreground" "--secondary" "--muted" "--accent" "--destructive" "--border" "--input" "--ring" "--card"; do
    if ! grep -q "$var" "$CSS_FILE" 2>/dev/null; then
      MISSING_VARS+=("$var")
    fi
  done
  
  if [[ ${#MISSING_VARS[@]} -eq 0 ]]; then
    pass "所有核心CSS变量已定义 (12/12)"
  elif [[ ${#MISSING_VARS[@]} -le 3 ]]; then
    warn "部分CSS变量缺失: ${MISSING_VARS[*]}"
  else
    fail "大量CSS变量缺失 (${#MISSING_VARS[@]}/12) — 这就是样式不生效的原因!"
    info "缺失: ${MISSING_VARS[*]}"
    info "修复: 重新运行 npx shadcn@latest init 或从 https://ui.shadcn.com/themes 复制CSS变量"
  fi
  
  # 检查 @tailwind 指令 (v3) 或 @import (v4)
  if grep -q "@tailwind base" "$CSS_FILE" 2>/dev/null; then
    pass "Tailwind v3 指令已配置 (@tailwind base/components/utilities)"
  elif grep -q '@import "tailwindcss"' "$CSS_FILE" 2>/dev/null || grep -q "@import 'tailwindcss'" "$CSS_FILE" 2>/dev/null; then
    pass "Tailwind v4 import 已配置"
  else
    warn "未检测到 Tailwind 指令/import"
  fi

  # 检查 dark 模式变量
  if grep -q "\.dark" "$CSS_FILE" 2>/dev/null || grep -q "@dark" "$CSS_FILE" 2>/dev/null; then
    pass "Dark mode CSS 变量已定义"
  else
    warn "未检测到 dark mode CSS 变量"
  fi
fi

# ────────────────────────────────────────────────────
# 3. CSS 导入链
# ────────────────────────────────────────────────────
echo ""
echo "🔗 [3/7] CSS 导入链 (layout.tsx → globals.css)"

LAYOUT_FILE=""
for f in "app/layout.tsx" "src/app/layout.tsx" "app/layout.jsx" "src/app/layout.jsx"; do
  if [[ -f "$f" ]]; then
    LAYOUT_FILE="$f"
    break
  fi
done

if [[ -z "$LAYOUT_FILE" ]]; then
  fail "找不到 layout.tsx / layout.jsx"
else
  if grep -q "globals.css\|globals\.css" "$LAYOUT_FILE" 2>/dev/null; then
    pass "layout 文件正确导入了 globals.css"
  else
    fail "layout 文件没有导入 globals.css — 所有样式都不会生效!"
    info "修复: 在 $LAYOUT_FILE 顶部添加 import './globals.css' 或 import '@/app/globals.css'"
  fi
fi

# ────────────────────────────────────────────────────
# 4. cn() 工具函数
# ────────────────────────────────────────────────────
echo ""
echo "🔧 [4/7] cn() 工具函数"

UTILS_FILE=""
for f in "lib/utils.ts" "src/lib/utils.ts" "lib/utils.js" "src/lib/utils.js"; do
  if [[ -f "$f" ]]; then
    UTILS_FILE="$f"
    break
  fi
done

if [[ -z "$UTILS_FILE" ]]; then
  fail "找不到 lib/utils.ts (cn() 函数)"
  info "修复: 运行 npx shadcn@latest init 会自动创建"
else
  if grep -q "clsx\|cn" "$UTILS_FILE" 2>/dev/null; then
    pass "cn() 工具函数已定义: $UTILS_FILE"
  else
    warn "utils 文件存在但可能缺少 cn() 函数"
  fi
fi

# ────────────────────────────────────────────────────
# 5. 已安装的组件
# ────────────────────────────────────────────────────
echo ""
echo "📦 [5/7] 已安装的 shadcn/ui 组件"

UI_DIR=""
for d in "components/ui" "src/components/ui" "packages/ui/src/components"; do
  if [[ -d "$d" ]]; then
    UI_DIR="$d"
    break
  fi
done

if [[ -z "$UI_DIR" ]]; then
  fail "找不到 components/ui 目录 — 没有安装任何 shadcn/ui 组件"
  info "修复: npx shadcn@latest add button card input dialog"
else
  COMPONENT_COUNT=$(find "$UI_DIR" -name "*.tsx" -o -name "*.jsx" 2>/dev/null | wc -l)
  if [[ $COMPONENT_COUNT -eq 0 ]]; then
    fail "components/ui 目录为空"
  elif [[ $COMPONENT_COUNT -lt 5 ]]; then
    warn "仅安装了 $COMPONENT_COUNT 个组件 (建议安装更多常用组件)"
  else
    pass "已安装 $COMPONENT_COUNT 个组件"
  fi
  
  # 列出已安装的组件
  info "已安装:"
  INSTALLED=""
  for f in "$UI_DIR"/*.tsx "$UI_DIR"/*.jsx; do
    if [[ -f "$f" ]]; then
      NAME=$(basename "$f" | sed 's/\.\(tsx\|jsx\)$//')
      INSTALLED="$INSTALLED $NAME"
    fi
  done
  echo "       $INSTALLED"
  
  # 推荐安装的核心组件
  CORE_COMPONENTS="button card dialog input label select tabs table badge alert dropdown-menu popover separator skeleton toast tooltip sheet breadcrumb checkbox radio-group switch textarea scroll-area avatar progress"
  MISSING_CORE=()
  for comp in $CORE_COMPONENTS; do
    FOUND=false
    for ext in tsx jsx; do
      if [[ -f "$UI_DIR/$comp.$ext" ]]; then
        FOUND=true
        break
      fi
    done
    if ! $FOUND; then
      MISSING_CORE+=("$comp")
    fi
  done
  
  if [[ ${#MISSING_CORE[@]} -gt 0 ]]; then
    echo ""
    warn "推荐安装的常用组件 (${#MISSING_CORE[@]}个未安装):"
    echo "       ${MISSING_CORE[*]}"
    echo ""
    info "一键安装: npx shadcn@latest add ${MISSING_CORE[*]}"
  fi
fi

# ────────────────────────────────────────────────────
# 6. 依赖包
# ────────────────────────────────────────────────────
echo ""
echo "📚 [6/7] 核心依赖包"

if [[ -f "package.json" ]]; then
  check_dep() {
    local dep=$1
    if grep -q "\"$dep\"" package.json 2>/dev/null; then
      pass "$dep"
    else
      fail "$dep 未安装"
      info "修复: npm install $dep"
    fi
  }
  
  check_dep "tailwindcss"
  check_dep "class-variance-authority"
  check_dep "clsx"
  check_dep "tailwind-merge"
  check_dep "lucide-react"
  
  # 可选但推荐
  if grep -q "\"@radix-ui" package.json 2>/dev/null; then
    RADIX_COUNT=$(grep -c "@radix-ui" package.json 2>/dev/null || echo 0)
    pass "Radix UI 包已安装 (${RADIX_COUNT}个)"
  else
    warn "未检测到 Radix UI 包 (安装shadcn组件时会自动添加)"
  fi
else
  fail "找不到 package.json"
fi

# ────────────────────────────────────────────────────
# 7. Tailwind 配置
# ────────────────────────────────────────────────────
echo ""
echo "⚙️  [7/7] Tailwind 配置"

# Tailwind v3
TW_CONFIG=""
for f in "tailwind.config.ts" "tailwind.config.js" "tailwind.config.mjs"; do
  if [[ -f "$f" ]]; then
    TW_CONFIG="$f"
    break
  fi
done

if [[ -n "$TW_CONFIG" ]]; then
  pass "Tailwind 配置文件: $TW_CONFIG (v3)"
  
  # 检查 content 路径是否包含 components
  if grep -q "components" "$TW_CONFIG" 2>/dev/null; then
    pass "content 路径包含 components 目录"
  else
    fail "content 路径可能不包含 components 目录 — shadcn组件样式不会生效!"
    info "修复: 在 tailwind.config 的 content 数组中添加 './components/**/*.{ts,tsx}'"
  fi
elif [[ -f "postcss.config.mjs" ]] || [[ -f "postcss.config.js" ]]; then
  # 可能是 Tailwind v4
  pass "检测到 PostCSS 配置 (可能是 Tailwind v4 — 不需要 content 配置)"
else
  warn "未检测到 Tailwind 配置文件"
fi

# ────────────────────────────────────────────────────
# CLAUDE.md 检查
# ────────────────────────────────────────────────────
echo ""
echo "📝 [额外] Claude Code 配置"

if [[ -f "CLAUDE.md" ]]; then
  if grep -qi "shadcn" "CLAUDE.md" 2>/dev/null; then
    pass "CLAUDE.md 包含 shadcn/ui 指令"
  else
    warn "CLAUDE.md 存在但未包含 shadcn/ui 使用指令"
  fi
else
  warn "CLAUDE.md 不存在 — Claude Code 不知道要使用 shadcn/ui"
  info "修复: 创建 CLAUDE.md 并添加 shadcn/ui 组件使用规范"
fi

# MCP 检查
if [[ -f ".mcp.json" ]]; then
  if grep -qi "shadcn" ".mcp.json" 2>/dev/null; then
    pass ".mcp.json 包含 shadcn MCP server"
  else
    warn ".mcp.json 存在但未配置 shadcn MCP server"
  fi
else
  warn ".mcp.json 不存在 — Claude Code 没有实时 shadcn 组件知识"
fi

# ────────────────────────────────────────────────────
# 总结
# ────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " 检测结果: ${GREEN}✓ ${PASS} 通过${NC}  ${RED}✗ ${FAIL} 失败${NC}  ${YELLOW}⚠ ${WARN} 警告${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $FAIL -eq 0 ]]; then
  echo -e " ${GREEN}🎉 shadcn/ui 配置正常!${NC}"
elif [[ $FAIL -le 2 ]]; then
  echo -e " ${YELLOW}⚡ 有少量问题需要修复，请查看上方的修复建议${NC}"
else
  echo -e " ${RED}❌ 有多个问题，shadcn/ui 可能无法正常工作${NC}"
  echo -e " ${BLUE}💡 建议: 在项目目录下运行 npx shadcn@latest init 重新初始化${NC}"
fi

echo ""
