"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { sessionApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Slider } from "@/components/ui/slider";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Plus,
  RefreshCw,
  Shield,
  Trash2,
  Zap,
  HeartPulse,
  KeyRound,
  ArrowRight,
  Loader2,
  ChevronDown,
  ChevronUp,
  Eye,
  MousePointerClick,
  GripHorizontal,
  RotateCcw,
  ListOrdered,
} from "lucide-react";
import { toast } from "sonner";

interface BrowserSession {
  id: string;
  provider_name: string;
  display_name: string;
  status: string;
  phone_number: string;
  last_used_at: string | null;
  last_health_check: string | null;
  health_check_message: string | null;
  created_at: string;
  updated_at: string;
}

interface AuthStatus {
  state: string;
  message?: string;
  screenshot?: string;
  captcha_type?: string;
  captcha_instruction?: string;
}

const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className: string }> = {
  created: { label: "已创建", variant: "secondary", className: "bg-gray-100 text-gray-700 border-gray-300" },
  authenticating: { label: "认证中", variant: "outline", className: "bg-yellow-50 text-yellow-700 border-yellow-300" },
  active: { label: "已激活", variant: "default", className: "bg-green-50 text-green-700 border-green-300" },
  expired: { label: "已过期", variant: "destructive", className: "bg-red-50 text-red-700 border-red-300" },
  error: { label: "错误", variant: "destructive", className: "bg-red-50 text-red-700 border-red-300" },
};

const PROVIDER_LABELS: Record<string, string> = {
  doubao: "豆包",
  deepseek: "DeepSeek",
};

const AUTH_STATE_LABELS: Record<string, string> = {
  starting: "启动中...",
  navigating: "导航到登录页...",
  sending_code: "发送验证码...",
  solving_captcha: "自动识别验证码...",
  manual_captcha: "需要人工处理验证码",
  waiting_for_code: "等待输入验证码",
  submitting_code: "提交验证码...",
  verifying: "验证中...",
  success: "认证成功",
  failed: "认证失败",
};

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ScreenshotCollapsible({ screenshot }: { screenshot: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="border rounded-lg overflow-hidden">
      <CollapsibleTrigger className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted/50 transition-colors">
        <span className="flex items-center gap-1.5">
          <Eye className="h-3.5 w-3.5" />
          当前页面截图
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="border-t">
          <img
            src={`data:image/png;base64,${screenshot}`}
            alt="认证截图"
            className="w-full"
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<BrowserSession[]>([]);
  const [loading, setLoading] = useState(true);

  // Create dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [createProvider, setCreateProvider] = useState("doubao");
  const [createName, setCreateName] = useState("");
  const [createPhone, setCreatePhone] = useState("");
  const [creating, setCreating] = useState(false);

  // Auth dialog state
  const [authOpen, setAuthOpen] = useState(false);
  const [authSession, setAuthSession] = useState<BrowserSession | null>(null);
  const [authPhone, setAuthPhone] = useState("");
  const [authStarted, setAuthStarted] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [authCode, setAuthCode] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const authPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Manual CAPTCHA state
  const [captchaData, setCaptchaData] = useState<{ screenshot: string; instruction: string; captcha_type: string } | null>(null);
  const [captchaSubmitting, setCaptchaSubmitting] = useState(false);
  const [clickPoints, setClickPoints] = useState<{ x: number; y: number }[]>([]);
  const [sliderValue, setSliderValue] = useState(50);
  const [captchaCountdown, setCaptchaCountdown] = useState(60);
  const [captchaImgNatural, setCaptchaImgNatural] = useState<{ w: number; h: number }>({ w: 1, h: 1 });

  // Delete confirm state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await sessionApi.list();
      setSessions(data);
    } catch {
      toast.error("获取会话列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh every 10s
  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, [fetchSessions]);

  // Auth status polling
  useEffect(() => {
    if (authStarted && authSession) {
      authPollingRef.current = setInterval(async () => {
        try {
          const status = await sessionApi.authStatus(authSession.id);
          setAuthStatus(status);
          // Fetch CAPTCHA data when entering manual_captcha state
          if (status.state === "manual_captcha" && authSession) {
            try {
              const data = await sessionApi.captchaData(authSession.id);
              setCaptchaData(data);
            } catch {
              // ignore
            }
          } else if (status.state !== "manual_captcha") {
            setCaptchaData(null);
          }

          if (status.state === "success" || status.state === "failed") {
            if (authPollingRef.current) clearInterval(authPollingRef.current);
            authPollingRef.current = null;
            if (status.state === "success") {
              toast.success("认证成功");
              fetchSessions();
            } else {
              toast.error(status.message || "认证失败");
            }
          }
        } catch {
          // ignore polling errors
        }
      }, 2000);
    }
    return () => {
      if (authPollingRef.current) {
        clearInterval(authPollingRef.current);
        authPollingRef.current = null;
      }
    };
  }, [authStarted, authSession, fetchSessions]);

  // Countdown timer for manual CAPTCHA (60s)
  useEffect(() => {
    if (authStatus?.state === "manual_captcha") {
      setCaptchaCountdown(60);
      const timer = setInterval(() => {
        setCaptchaCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [authStatus?.state, captchaData?.screenshot]);

  const handleCreate = async () => {
    if (!createName.trim()) {
      toast.error("请输入显示名称");
      return;
    }
    setCreating(true);
    try {
      await sessionApi.create({
        provider_name: createProvider,
        display_name: createName.trim(),
        phone_number: createPhone.trim() || undefined,
      });
      toast.success("会话创建成功");
      setCreateOpen(false);
      setCreateName("");
      setCreatePhone("");
      setCreateProvider("doubao");
      fetchSessions();
    } catch {
      toast.error("创建会话失败");
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (id: string) => {
    try {
      await sessionApi.activate(id);
      toast.success("会话已激活");
      fetchSessions();
    } catch {
      toast.error("激活失败");
    }
  };

  const handleHealthCheck = async (id: string) => {
    try {
      await sessionApi.healthCheck(id);
      toast.success("健康检查完成");
      fetchSessions();
    } catch {
      toast.error("健康检查失败");
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await sessionApi.delete(deleteId);
      toast.success("会话已删除");
      setDeleteId(null);
      fetchSessions();
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleting(false);
    }
  };

  const openAuthDialog = (session: BrowserSession) => {
    setAuthSession(session);
    setAuthPhone(session.phone_number || "");
    setAuthStarted(false);
    setAuthStatus(null);
    setAuthCode("");
    setAuthOpen(true);
  };

  const handleAuthStart = async () => {
    if (!authSession) return;
    if (!authPhone.trim()) {
      toast.error("请输入手机号");
      return;
    }
    setAuthSubmitting(true);
    try {
      await sessionApi.authStart(authSession.id, authPhone.trim());
      setAuthStarted(true);
      toast.success("认证流程已启动");
    } catch {
      toast.error("启动认证失败");
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleAuthCode = async () => {
    if (!authSession || !authCode.trim()) return;
    setAuthSubmitting(true);
    try {
      await sessionApi.authCode(authSession.id, authCode.trim());
      toast.success("验证码已提交");
      setAuthCode("");
    } catch {
      toast.error("提交验证码失败");
    } finally {
      setAuthSubmitting(false);
    }
  };

  const closeAuthDialog = () => {
    setAuthOpen(false);
    if (authPollingRef.current) {
      clearInterval(authPollingRef.current);
      authPollingRef.current = null;
    }
    setAuthStarted(false);
    setAuthStatus(null);
    setAuthSession(null);
    setCaptchaData(null);
    setCaptchaSubmitting(false);
    setClickPoints([]);
    setSliderValue(50);
    setCaptchaCountdown(60);
    setCaptchaImgNatural({ w: 1, h: 1 });
  };

  const getStatusBadge = (status: string) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.created;
    return (
      <Badge variant={config.variant} className={config.className}>
        {config.label}
      </Badge>
    );
  };

  const getProviderBadge = (provider: string) => {
    const label = PROVIDER_LABELS[provider] || provider;
    const className = provider === "doubao"
      ? "bg-blue-50 text-blue-700 border-blue-300"
      : "bg-emerald-50 text-emerald-700 border-emerald-300";
    return (
      <Badge variant="outline" className={className}>
        {label}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">会话管理</h1>
          <p className="text-muted-foreground mt-1">
            管理浏览器会话，用于豆包/DeepSeek等平台的自动化监测
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchSessions}>
            <RefreshCw className="h-4 w-4 mr-1" />
            刷新
          </Button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-1" />
                新建会话
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>新建浏览器会话</DialogTitle>
                <DialogDescription>
                  创建一个新的浏览器会话，用于平台自动化监测
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">平台</label>
                  <Select value={createProvider} onValueChange={setCreateProvider}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="doubao">豆包</SelectItem>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">显示名称</label>
                  <Input
                    placeholder="例如：豆包主账号"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    手机号 <span className="text-muted-foreground font-normal">(可选)</span>
                  </label>
                  <Input
                    placeholder="用于登录认证的手机号"
                    value={createPhone}
                    onChange={(e) => setCreatePhone(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleCreate} disabled={creating}>
                  {creating && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  创建
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Flow Guide */}
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-indigo-500" />
            会话配置流程
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-50 border">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold">1</span>
              <span>创建会话</span>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-50 border">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold">2</span>
              <span>认证登录</span>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-50 border">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold">3</span>
              <span>激活使用</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sessions Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">会话列表</CardTitle>
          <CardDescription>共 {sessions.length} 个会话</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              加载中...
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              暂无会话，点击"新建会话"开始
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>平台</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>手机号</TableHead>
                  <TableHead>最近健康检查</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell className="font-medium">{session.display_name}</TableCell>
                    <TableCell>{getProviderBadge(session.provider_name)}</TableCell>
                    <TableCell>{getStatusBadge(session.status)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {session.phone_number || "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(session.last_health_check)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(session.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {session.status === "created" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleActivate(session.id)}
                          >
                            <Zap className="h-3.5 w-3.5 mr-1" />
                            激活
                          </Button>
                        )}
                        {session.status === "active" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleHealthCheck(session.id)}
                          >
                            <HeartPulse className="h-3.5 w-3.5 mr-1" />
                            健康检查
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openAuthDialog(session)}
                        >
                          <KeyRound className="h-3.5 w-3.5 mr-1" />
                          认证
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => setDeleteId(session.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除该会话吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Auth Dialog — responsive: wider when CAPTCHA active */}
      <Dialog open={authOpen} onOpenChange={(open) => !open && closeAuthDialog()}>
        <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              会话认证 - {authSession?.display_name}
              {authStatus?.state === "manual_captcha" && (
                <span className={`ml-auto text-xs font-mono font-bold px-2.5 py-1 rounded-full ${
                  captchaCountdown <= 15 ? "bg-red-100 text-red-700 animate-pulse" : "bg-orange-100 text-orange-700"
                }`}>
                  {captchaCountdown}s
                </span>
              )}
            </DialogTitle>
            {!authStarted && (
              <DialogDescription>
                通过手机验证码完成平台登录认证
              </DialogDescription>
            )}
          </DialogHeader>

          <div className="space-y-4 py-1">
            {!authStarted ? (
              /* Pre-start: phone input */
              <div className="space-y-4">
                {authSession?.status === "active" && (
                  <div className="rounded-lg border border-green-200 bg-green-50/50 p-3 text-sm text-green-700">
                    该会话当前状态为「已激活」。点击「开始认证」将自动检测登录状态，若已登录则无需重新输入验证码。
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium">手机号</label>
                  <Input
                    placeholder="请输入手机号"
                    value={authPhone}
                    onChange={(e) => setAuthPhone(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAuthStart()}
                  />
                </div>
                <Button
                  className="w-full"
                  onClick={handleAuthStart}
                  disabled={authSubmitting}
                >
                  {authSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  {authSession?.status === "active" ? "检测并认证" : "开始认证"}
                </Button>
              </div>
            ) : (
              /* Auth in progress */
              <div className="space-y-4">
                {/* ── 8-step vertical progress list ── */}
                {(() => {
                  const STEPS = ["starting", "navigating", "sending_code", "solving_captcha", "waiting_for_code", "submitting_code", "verifying", "success"];
                  const STEP_LABELS: Record<string, string> = {
                    starting: "启动浏览器",
                    navigating: "导航到登录页",
                    sending_code: "发送验证码",
                    solving_captcha: "识别验证码",
                    waiting_for_code: "等待输入验证码",
                    submitting_code: "提交验证码",
                    verifying: "验证登录状态",
                    success: "认证完成",
                  };
                  const currentState = authStatus?.state || "starting";
                  const mappedState = currentState === "manual_captcha" ? "solving_captcha" : currentState;
                  const currentIdx = STEPS.indexOf(mappedState);
                  const isTerminal = currentState === "success" || currentState === "failed";
                  const isCaptchaMode = currentState === "manual_captcha";

                  // In CAPTCHA mode, collapse to single-line summary (expandable)
                  if (isCaptchaMode) {
                    return (
                      <Collapsible className="border rounded-lg">
                        <CollapsibleTrigger className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/50 transition-colors">
                          <span className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                            <span className="font-medium text-foreground">步骤 4/8 — 需要人工处理验证码</span>
                          </span>
                          <ChevronDown className="h-3.5 w-3.5" />
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="px-3 pb-2 space-y-0.5">
                            {STEPS.map((step, idx) => {
                              const done = idx < currentIdx;
                              const active = idx === currentIdx;
                              return (
                                <div key={step} className={`flex items-center gap-2 py-1 text-xs ${
                                  active ? "text-foreground font-medium" : done ? "text-green-600" : "text-muted-foreground"
                                }`}>
                                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                                    active ? "bg-orange-500" : done ? "bg-green-500" : "bg-gray-300"
                                  }`} />
                                  {STEP_LABELS[step]}
                                </div>
                              );
                            })}
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    );
                  }

                  return (
                    <div className="space-y-0.5">
                      {STEPS.map((step, idx) => {
                        const done = isTerminal ? (currentState === "success") : idx < currentIdx;
                        const active = !isTerminal && idx === currentIdx;
                        const isFailed = isTerminal && currentState === "failed" && idx === currentIdx;
                        return (
                          <div key={step} className={`flex items-center gap-2 py-1 text-sm ${
                            isFailed ? "text-red-600 font-medium"
                              : active ? "text-foreground font-medium"
                              : done ? "text-green-600"
                              : "text-muted-foreground"
                          }`}>
                            <div className={`w-2 h-2 rounded-full shrink-0 ${
                              isFailed ? "bg-red-500"
                                : active ? "bg-indigo-500 animate-pulse"
                                : done ? "bg-green-500"
                                : "bg-gray-300"
                            }`} />
                            {STEP_LABELS[step]}
                            {active && !isTerminal && (
                              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                            )}
                            {isFailed && authStatus?.message && (
                              <span className="font-normal text-muted-foreground">— {authStatus.message}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                {/* ── Manual CAPTCHA interaction (primary focus area) ── */}
                {authStatus?.state === "manual_captcha" && captchaData?.screenshot && (
                  <div className="space-y-3 border rounded-lg p-4 bg-muted/50 border-l-4 border-l-orange-400">
                    {/* Header: type badge on its own line, instruction below */}
                    <div className="space-y-2">
                      {(() => {
                        const cType = captchaData.captcha_type || authStatus.captcha_type || "click_target";
                        const typeConfig: Record<string, { label: string; icon: React.ReactNode }> = {
                          click_target: { label: "点击目标", icon: <MousePointerClick className="h-3.5 w-3.5" /> },
                          slider_puzzle: { label: "滑块拼图", icon: <GripHorizontal className="h-3.5 w-3.5" /> },
                          text_order: { label: "文字顺序", icon: <ListOrdered className="h-3.5 w-3.5" /> },
                          rotate: { label: "旋转对齐", icon: <RotateCcw className="h-3.5 w-3.5" /> },
                        };
                        const cfg = typeConfig[cType] || typeConfig.click_target;
                        return (
                          <Badge variant="outline" className="gap-1">
                            {cfg.icon} {cfg.label}
                          </Badge>
                        );
                      })()}
                      <p className="text-sm font-medium">
                        {captchaData.instruction || authStatus.captcha_instruction || "请在下方图片上操作验证码"}
                      </p>
                    </div>

                    {/* CAPTCHA image + controls */}
                    {(() => {
                      const cType = captchaData.captcha_type || authStatus.captcha_type || "click_target";

                      const getImageCoords = (e: React.MouseEvent<HTMLDivElement>) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        const img = e.currentTarget.querySelector("img");
                        if (!img) return null;
                        const scaleX = img.naturalWidth / rect.width;
                        const scaleY = img.naturalHeight / rect.height;
                        return {
                          x: Math.round((e.clientX - rect.left) * scaleX),
                          y: Math.round((e.clientY - rect.top) * scaleY),
                        };
                      };

                      const captchaImg = (
                        <img
                          src={`data:image/png;base64,${captchaData.screenshot}`}
                          alt="验证码"
                          className="w-full select-none"
                          draggable={false}
                          onLoad={(e) => {
                            const img = e.currentTarget;
                            setCaptchaImgNatural({ w: img.naturalWidth, h: img.naturalHeight });
                          }}
                        />
                      );

                      const loadingOverlay = captchaSubmitting && (
                        <div className="absolute inset-0 bg-white/60 flex items-center justify-center">
                          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                      );

                      // Refresh button (shared across all types, placed below image)
                      const refreshBtn = (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            if (!authSession) return;
                            setCaptchaSubmitting(true);
                            try {
                              await sessionApi.captchaAction(authSession.id, { type: "refresh" });
                              toast.success("已请求刷新验证码");
                              setClickPoints([]);
                              setSliderValue(50);
                            } catch { toast.error("刷新失败"); }
                            finally { setCaptchaSubmitting(false); }
                          }}
                          disabled={captchaSubmitting}
                        >
                          <RefreshCw className="h-3.5 w-3.5 mr-1" />
                          刷新
                        </Button>
                      );

                      // === click_target or unknown: click anywhere on image ===
                      if (cType === "click_target" || !["slider_puzzle", "text_order", "rotate"].includes(cType)) {
                        return (
                          <>
                            <div
                              className="border rounded-lg overflow-hidden cursor-crosshair relative bg-white"
                              onClick={async (e) => {
                                if (captchaSubmitting || !authSession) return;
                                const coords = getImageCoords(e);
                                if (!coords) return;
                                setCaptchaSubmitting(true);
                                try {
                                  await sessionApi.captchaAction(authSession.id, { type: "click", x: coords.x, y: coords.y });
                                  toast.success(`已点击 (${coords.x}, ${coords.y})`);
                                } catch { toast.error("提交失败"); }
                                finally { setCaptchaSubmitting(false); }
                              }}
                            >
                              {captchaImg}
                              {loadingOverlay}
                            </div>
                            <div className="flex justify-end">
                              {refreshBtn}
                            </div>
                          </>
                        );
                      }

                      // === text_order: multi-click with numbered markers ===
                      if (cType === "text_order") {
                        return (
                          <>
                            <div
                              className="border rounded-lg overflow-hidden cursor-crosshair relative bg-white"
                              onClick={(e) => {
                                if (captchaSubmitting) return;
                                const coords = getImageCoords(e);
                                if (!coords) return;
                                setClickPoints((prev) => [...prev, { x: coords.x, y: coords.y }]);
                              }}
                            >
                              {captchaImg}
                              {clickPoints.map((pt, idx) => (
                                <div
                                  key={idx}
                                  className="absolute w-7 h-7 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-bold pointer-events-none shadow-lg border-2 border-white"
                                  style={{
                                    left: `${(pt.x / captchaImgNatural.w) * 100}%`,
                                    top: `${(pt.y / captchaImgNatural.h) * 100}%`,
                                  }}
                                >
                                  {idx + 1}
                                </div>
                              ))}
                              {loadingOverlay}
                            </div>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setClickPoints([])}
                                disabled={clickPoints.length === 0}
                              >
                                清除标记
                              </Button>
                              <Button
                                size="sm"
                                onClick={async () => {
                                  if (!authSession || clickPoints.length === 0) return;
                                  setCaptchaSubmitting(true);
                                  try {
                                    await sessionApi.captchaAction(authSession.id, { type: "click_sequence", points: clickPoints });
                                    toast.success(`已提交 ${clickPoints.length} 个点击`);
                                    setClickPoints([]);
                                  } catch { toast.error("提交失败"); }
                                  finally { setCaptchaSubmitting(false); }
                                }}
                                disabled={captchaSubmitting || clickPoints.length === 0}
                              >
                                {captchaSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                                提交 ({clickPoints.length} 点)
                              </Button>
                              <div className="ml-auto">{refreshBtn}</div>
                            </div>
                          </>
                        );
                      }

                      // === slider_puzzle: image + slider ===
                      if (cType === "slider_puzzle") {
                        return (
                          <>
                            <div className="border rounded-lg overflow-hidden relative bg-white">
                              {captchaImg}
                              {loadingOverlay}
                            </div>
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                                <span>滑动距离</span>
                                <span className="font-mono bg-muted px-2 py-0.5 rounded">{sliderValue}%</span>
                              </div>
                              <Slider
                                min={0} max={100} step={1}
                                value={[sliderValue]}
                                onValueChange={(v) => setSliderValue(v[0])}
                              />
                            </div>
                            <div className="flex gap-2">
                              <Button
                                className="flex-1"
                                onClick={async () => {
                                  if (!authSession) return;
                                  setCaptchaSubmitting(true);
                                  const dragDistance = Math.round(sliderValue * 3);
                                  try {
                                    await sessionApi.captchaAction(authSession.id, {
                                      type: "drag", start_x: 10, start_y: 150,
                                      end_x: 10 + dragDistance, end_y: 150,
                                    });
                                    toast.success(`已拖动 ${sliderValue}%`);
                                  } catch { toast.error("提交失败"); }
                                  finally { setCaptchaSubmitting(false); }
                                }}
                                disabled={captchaSubmitting}
                              >
                                {captchaSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                                提交滑块
                              </Button>
                              {refreshBtn}
                            </div>
                          </>
                        );
                      }

                      // === rotate: image + angle slider ===
                      return (
                        <>
                          <div className="border rounded-lg overflow-hidden relative bg-white">
                            {captchaImg}
                            {loadingOverlay}
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                              <span>旋转角度</span>
                              <span className="font-mono bg-muted px-2 py-0.5 rounded">{sliderValue}°</span>
                            </div>
                            <Slider
                              min={0} max={360} step={1}
                              value={[sliderValue]}
                              onValueChange={(v) => setSliderValue(v[0])}
                            />
                          </div>
                          <div className="flex gap-2">
                            <Button
                              className="flex-1"
                              onClick={async () => {
                                if (!authSession) return;
                                setCaptchaSubmitting(true);
                                const dragDistance = Math.round((sliderValue / 360) * 300);
                                try {
                                  await sessionApi.captchaAction(authSession.id, {
                                    type: "drag", start_x: 10, start_y: 150,
                                    end_x: 10 + dragDistance, end_y: 150,
                                  });
                                  toast.success(`已旋转 ${sliderValue}°`);
                                } catch { toast.error("提交失败"); }
                                finally { setCaptchaSubmitting(false); }
                              }}
                              disabled={captchaSubmitting}
                            >
                              {captchaSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                              提交旋转
                            </Button>
                            {refreshBtn}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}

                {/* ── Verification code input — always visible, active when waiting ── */}
                {(() => {
                  const isActive = authStatus?.state === "waiting_for_code";
                  const isTerminal = authStatus?.state === "success" || authStatus?.state === "failed";
                  if (isTerminal) return null;
                  return (
                    <div className={`space-y-2 border rounded-lg p-4 transition-colors ${
                      isActive ? "border-yellow-400 bg-yellow-50/50 ring-1 ring-yellow-200" : "border-muted bg-muted/30"
                    }`}>
                      <label className={`text-sm font-medium ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
                        {isActive ? "请输入收到的短信验证码" : "短信验证码（等待中...）"}
                      </label>
                      <div className="flex gap-2">
                        <Input
                          placeholder="输入 6 位验证码"
                          value={authCode}
                          onChange={(e) => setAuthCode(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && isActive && handleAuthCode()}
                          disabled={!isActive}
                        />
                        <Button
                          onClick={handleAuthCode}
                          disabled={!isActive || authSubmitting || !authCode.trim()}
                        >
                          {authSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                          提交
                        </Button>
                      </div>
                    </div>
                  );
                })()}

                {/* ── Screenshot — collapsible ── */}
                {authStatus?.screenshot && (
                  <ScreenshotCollapsible screenshot={authStatus.screenshot} />
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeAuthDialog}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
