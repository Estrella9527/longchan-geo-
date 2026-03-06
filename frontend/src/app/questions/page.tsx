"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { DataTable } from "@/components/data-table";
import {
  Plus, Search, Upload, Sparkles, Trash2, Pencil, GripVertical,
  FileUp, Check, X, ChevronRight, MessageSquare, Download,
} from "lucide-react";
import { brandApi, questionSetApi, questionApi } from "@/lib/api";
import type { Brand, QuestionSet, Question } from "@/types";

// --- Constants ---
const QUESTION_CATEGORIES = [
  { value: "品牌提及推荐", label: "品牌提及推荐" },
  { value: "品牌排行", label: "品牌排行" },
  { value: "品牌用户情感", label: "品牌用户情感" },
] as const;

// --- Schemas ---
const questionSetSchema = z.object({
  brand_id: z.string().min(1, "请选择品牌"),
  name: z.string().min(1, "请输入问题集名称"),
  description: z.string().optional(),
});
type QSFormValues = z.infer<typeof questionSetSchema>;

const questionCreateSchema = z.object({
  question_set_id: z.string().min(1, "请选择问题集"),
  brand_id: z.string().min(1, "请选择品牌"),
  category: z.string().optional(),
  content: z.string().min(1, "请输入问题内容").max(500, "问题内容不能超过500字"),
});
type QuestionCreateValues = z.infer<typeof questionCreateSchema>;

// --- Main Page ---
export default function QuestionsPage() {
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [qsDialogOpen, setQsDialogOpen] = useState(false);
  const [editingQS, setEditingQS] = useState<QuestionSet | null>(null);
  const [filterBrandId, setFilterBrandId] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");

  // Question-level state
  const [selectedQS, setSelectedQS] = useState<QuestionSet | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);

  // Creation drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState("single");

  // Inline edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editCategory, setEditCategory] = useState("");

  // Drag state
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  // Inline QS create (from drawer)
  const [inlineQSDialogOpen, setInlineQSDialogOpen] = useState(false);

  const qsForm = useForm<QSFormValues>({
    resolver: zodResolver(questionSetSchema),
    defaultValues: { brand_id: "", name: "", description: "" },
  });

  const brandNameMap = useMemo(
    () => Object.fromEntries(brands.map((b) => [b.id, b.name])),
    [brands]
  );

  // --- Data fetching ---
  const fetchQuestionSets = useCallback(async () => {
    try {
      const [qsRes, brandRes] = await Promise.all([
        questionSetApi.list({ brand_id: filterBrandId || undefined }),
        brandApi.list(),
      ]);
      setQuestionSets(qsRes.data);
      setBrands(brandRes.data);
    } catch {
      toast.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [filterBrandId]);

  useEffect(() => { fetchQuestionSets(); }, [fetchQuestionSets]);

  const fetchQuestions = useCallback(async (qsId: string) => {
    setQuestionsLoading(true);
    try {
      const res = await questionApi.list(qsId);
      setQuestions(res.data);
    } catch {
      toast.error("加载问题列表失败");
    } finally {
      setQuestionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedQS) fetchQuestions(selectedQS.id);
    else setQuestions([]);
  }, [selectedQS, fetchQuestions]);

  // Filtered question sets
  const filteredSets = useMemo(() => {
    if (!searchKeyword.trim()) return questionSets;
    const kw = searchKeyword.toLowerCase();
    return questionSets.filter(
      (qs) => qs.name.toLowerCase().includes(kw) || (brandNameMap[qs.brand_id] || "").toLowerCase().includes(kw)
    );
  }, [questionSets, searchKeyword, brandNameMap]);

  // --- Question Set CRUD ---
  const openCreateQS = (prefillBrandId?: string) => {
    setEditingQS(null);
    qsForm.reset({ brand_id: prefillBrandId || "", name: "", description: "" });
    setQsDialogOpen(true);
  };

  const openEditQS = (qs: QuestionSet) => {
    setEditingQS(qs);
    qsForm.reset({ brand_id: qs.brand_id, name: qs.name, description: qs.description });
    setQsDialogOpen(true);
  };

  const onSubmitQS = async (values: QSFormValues) => {
    try {
      if (editingQS) {
        await questionSetApi.update(editingQS.id, { name: values.name, description: values.description });
        toast.success("问题集已更新");
      } else {
        await questionSetApi.create(values);
        toast.success("问题集已创建");
      }
      setQsDialogOpen(false);
      setInlineQSDialogOpen(false);
      qsForm.reset();
      fetchQuestionSets();
    } catch {
      toast.error(editingQS ? "更新失败" : "创建失败");
    }
  };

  const handleDeleteQS = async (id: string) => {
    try {
      await questionSetApi.delete(id);
      toast.success("已删除");
      if (selectedQS?.id === id) { setSelectedQS(null); setQuestions([]); }
      fetchQuestionSets();
    } catch {
      toast.error("删除失败");
    }
  };

  // --- Question inline edit ---
  const startEdit = (q: Question) => {
    setEditingId(q.id);
    setEditContent(q.content);
    setEditCategory(q.category);
  };
  const cancelEdit = () => { setEditingId(null); setEditContent(""); setEditCategory(""); };
  const saveEdit = async () => {
    if (!editingId) return;
    try {
      await questionApi.update(editingId, { content: editContent.trim(), category: editCategory.trim() });
      toast.success("已更新");
      cancelEdit();
      if (selectedQS) fetchQuestions(selectedQS.id);
    } catch {
      toast.error("更新失败");
    }
  };

  const handleDeleteQuestion = async (id: string) => {
    if (!selectedQS) return;
    try {
      await questionApi.delete(id);
      toast.success("已删除");
      fetchQuestions(selectedQS.id);
      fetchQuestionSets();
    } catch {
      toast.error("删除失败");
    }
  };

  // --- Drag & Drop ---
  const handleDragStart = (index: number) => setDragIndex(index);
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (dragIndex === null || dragIndex === index) return;
    const newList = [...questions];
    const [dragged] = newList.splice(dragIndex, 1);
    newList.splice(index, 0, dragged);
    setQuestions(newList);
    setDragIndex(index);
  };
  const handleDragEnd = async () => {
    setDragIndex(null);
    if (!selectedQS) return;
    try {
      await questionApi.reorder({ question_ids: questions.map((q) => q.id) });
    } catch {
      toast.error("排序失败");
      fetchQuestions(selectedQS.id);
    }
  };

  // --- Open create drawer ---
  const openCreateDrawer = () => {
    setDrawerTab("single");
    setDrawerOpen(true);
  };

  // --- Question Set Table ---
  const qsColumns: ColumnDef<QuestionSet>[] = [
    {
      accessorKey: "name", header: "问题集名称",
      cell: ({ row }) => (
        <button
          className="text-left font-medium hover:underline text-primary"
          onClick={(e) => { e.stopPropagation(); setSelectedQS(row.original); }}
        >
          {row.original.name}
        </button>
      ),
    },
    { accessorKey: "brand_id", header: "关联品牌", cell: ({ row }) => brandNameMap[row.getValue("brand_id") as string] || "-" },
    {
      accessorKey: "question_count", header: "问题数",
      cell: ({ row }) => <Badge variant="secondary">{row.getValue("question_count") as number}</Badge>,
    },
    { accessorKey: "created_at", header: "创建时间", cell: ({ row }) => new Date(row.getValue("created_at") as string).toLocaleDateString("zh-CN") },
    {
      id: "actions",
      header: () => <div className="text-right">操作</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEditQS(row.original)} title="编辑">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" title="删除">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>确认删除</AlertDialogTitle>
                <AlertDialogDescription>确定要删除问题集「{row.original.name}」吗？该问题集下的所有问题也将被删除，此操作不可撤销。</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction onClick={() => handleDeleteQS(row.original.id)}>删除</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      ),
    },
  ];

  if (loading) {
    return <div className="space-y-4"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">问题管理</h1>
          <p className="text-sm text-muted-foreground">管理品牌问题集和问题内容</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => openCreateQS()}>
            <Plus className="mr-2 h-4 w-4" />
            新建问题集
          </Button>
          <Button onClick={openCreateDrawer}>
            <Plus className="mr-2 h-4 w-4" />
            创建问题
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索问题集..."
            className="pl-9"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
          />
        </div>
        <Select value={filterBrandId} onValueChange={(v) => setFilterBrandId(v === "all" ? "" : v)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="所有品牌" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有品牌</SelectItem>
            {brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Question Sets Table */}
      <DataTable columns={qsColumns} data={filteredSets} emptyMessage="暂无问题集，点击右上角「新建问题集」开始" />

      {/* Selected Question Set Detail Panel */}
      {selectedQS && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-lg">{selectedQS.name}</CardTitle>
                    <CardDescription>
                      {brandNameMap[selectedQS.brand_id] || "未知品牌"}
                      {selectedQS.description && ` · ${selectedQS.description}`}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => { setDrawerOpen(true); setDrawerTab("single"); }}>
                    <Plus className="mr-1 h-3.5 w-3.5" />
                    添加问题
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => { setSelectedQS(null); setQuestions([]); }}>
                    <X className="mr-1 h-3.5 w-3.5" />
                    关闭
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Questions List */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  <MessageSquare className="mr-2 inline h-4 w-4" />
                  问题列表
                  <Badge variant="secondary" className="ml-2">{questions.length}</Badge>
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              {questionsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" />
                </div>
              ) : questions.length === 0 ? (
                <div className="flex h-20 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                  该问题集暂无问题，点击上方「添加问题」或右上角「创建问题」开始
                </div>
              ) : (
                <div className="space-y-1">
                  {questions.map((q, index) => (
                    <div
                      key={q.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={`group flex items-center gap-2 rounded-md border px-3 py-2 transition-colors ${
                        dragIndex === index ? "border-primary bg-accent" : "hover:bg-muted/50"
                      }`}
                    >
                      <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-muted-foreground opacity-0 group-hover:opacity-100" />
                      <span className="w-8 shrink-0 text-xs text-muted-foreground">{index + 1}</span>

                      {editingId === q.id ? (
                        <>
                          <Input
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            className="h-8 flex-1"
                            maxLength={500}
                            autoFocus
                            onKeyDown={(e) => { if (e.key === "Enter") saveEdit(); if (e.key === "Escape") cancelEdit(); }}
                          />
                          <Select value={editCategory} onValueChange={setEditCategory}>
                            <SelectTrigger className="h-8 w-32">
                              <SelectValue placeholder="分类" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value=" ">无分类</SelectItem>
                              {QUESTION_CATEGORIES.map((c) => (
                                <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={saveEdit}>
                            <Check className="h-3.5 w-3.5 text-green-600" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={cancelEdit}>
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      ) : (
                        <>
                          <span className="flex-1 text-sm">{q.content}</span>
                          {q.category && <Badge variant="outline" className="shrink-0">{q.category}</Badge>}
                          <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100" onClick={() => startEdit(q)} title="编辑">
                            <Pencil className="h-3 w-3" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive opacity-0 group-hover:opacity-100" title="删除">
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>确认删除</AlertDialogTitle>
                                <AlertDialogDescription>确定要删除该问题吗？此操作不可撤销。</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDeleteQuestion(q.id)}>删除</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* === Create Question Sheet (Drawer) === */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>创建问题</SheetTitle>
            <SheetDescription>创建问题集和问题的内容信息</SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <Tabs value={drawerTab} onValueChange={setDrawerTab}>
              <TabsList className="mb-4 w-full">
                <TabsTrigger value="single" className="flex-1">单条创建</TabsTrigger>
                <TabsTrigger value="batch" className="flex-1">批量创建</TabsTrigger>
                <TabsTrigger value="ai" className="flex-1">AI生成</TabsTrigger>
              </TabsList>

              <TabsContent value="single">
                <SingleCreateForm
                  brands={brands}
                  questionSets={questionSets}
                  selectedQS={selectedQS}
                  onCreated={() => {
                    fetchQuestionSets();
                    if (selectedQS) fetchQuestions(selectedQS.id);
                  }}
                  onClose={() => setDrawerOpen(false)}
                  onCreateQS={(brandId) => { openCreateQS(brandId); setInlineQSDialogOpen(true); }}
                />
              </TabsContent>

              <TabsContent value="batch">
                <BatchCreateForm
                  brands={brands}
                  questionSets={questionSets}
                  selectedQS={selectedQS}
                  onCreated={() => {
                    fetchQuestionSets();
                    if (selectedQS) fetchQuestions(selectedQS.id);
                  }}
                  onClose={() => setDrawerOpen(false)}
                />
              </TabsContent>

              <TabsContent value="ai">
                <AIGenerateForm
                  brands={brands}
                  questionSets={questionSets}
                  selectedQS={selectedQS}
                  brandNameMap={brandNameMap}
                  onCreated={() => {
                    fetchQuestionSets();
                    if (selectedQS) fetchQuestions(selectedQS.id);
                  }}
                  onClose={() => setDrawerOpen(false)}
                />
              </TabsContent>
            </Tabs>
          </div>
        </SheetContent>
      </Sheet>

      {/* Question Set Create/Edit Dialog */}
      <Dialog open={qsDialogOpen} onOpenChange={(open) => { setQsDialogOpen(open); if (!open) { qsForm.reset(); setEditingQS(null); } }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingQS ? "编辑问题集" : "新建问题集"}</DialogTitle>
            <DialogDescription>{editingQS ? "修改问题集信息" : "为品牌创建新的问题集"}</DialogDescription>
          </DialogHeader>
          <Form {...qsForm}>
            <form onSubmit={qsForm.handleSubmit(onSubmitQS)} className="space-y-4">
              <FormField control={qsForm.control} name="brand_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>关联品牌</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={!!editingQS}>
                    <FormControl><SelectTrigger><SelectValue placeholder="选择品牌" /></SelectTrigger></FormControl>
                    <SelectContent>
                      {brands.length === 0 ? <SelectItem value="none" disabled>请先创建品牌</SelectItem>
                        : brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={qsForm.control} name="name" render={({ field }) => (
                <FormItem><FormLabel>问题集名称</FormLabel><FormControl><Input placeholder="请输入问题集名称" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={qsForm.control} name="description" render={({ field }) => (
                <FormItem><FormLabel>描述</FormLabel><FormControl><Textarea placeholder="问题集描述（可选）" rows={2} {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => { setQsDialogOpen(false); setInlineQSDialogOpen(false); }}>取消</Button>
                <Button type="submit">{editingQS ? "保存修改" : "确认创建"}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================
// Single Create Form (inside drawer)
// ============================================================
function SingleCreateForm({
  brands, questionSets, selectedQS, onCreated, onClose, onCreateQS,
}: {
  brands: Brand[];
  questionSets: QuestionSet[];
  selectedQS: QuestionSet | null;
  onCreated: () => void;
  onClose: () => void;
  onCreateQS: (brandId: string) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [brandSearch, setBrandSearch] = useState("");

  const form = useForm<QuestionCreateValues>({
    resolver: zodResolver(questionCreateSchema),
    defaultValues: {
      brand_id: selectedQS?.brand_id || "",
      question_set_id: selectedQS?.id || "",
      category: "",
      content: "",
    },
  });

  const watchBrandId = form.watch("brand_id");
  const filteredBrands = useMemo(() => {
    if (!brandSearch.trim()) return brands;
    const kw = brandSearch.toLowerCase();
    return brands.filter((b) => b.name.toLowerCase().includes(kw));
  }, [brands, brandSearch]);

  const filteredQSets = useMemo(
    () => questionSets.filter((qs) => qs.brand_id === watchBrandId),
    [questionSets, watchBrandId]
  );

  // Reset question_set when brand changes
  useEffect(() => {
    if (watchBrandId && !filteredQSets.find((qs) => qs.id === form.getValues("question_set_id"))) {
      form.setValue("question_set_id", filteredQSets.length === 1 ? filteredQSets[0].id : "");
    }
  }, [watchBrandId, filteredQSets, form]);

  const onSubmit = async (values: QuestionCreateValues) => {
    setSubmitting(true);
    try {
      await questionApi.create({
        question_set_id: values.question_set_id,
        content: values.content.trim(),
        category: values.category || undefined,
      });
      toast.success("问题已创建");
      form.reset({ ...values, content: "", category: "" });
      onCreated();
    } catch {
      toast.error("创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const contentLength = form.watch("content")?.length || 0;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        {/* Brand */}
        <FormField control={form.control} name="brand_id" render={({ field }) => (
          <FormItem>
            <FormLabel>品牌 <span className="text-destructive">*</span></FormLabel>
            <Select onValueChange={(v) => { field.onChange(v); setBrandSearch(""); }} value={field.value}>
              <FormControl><SelectTrigger><SelectValue placeholder="选择品牌" /></SelectTrigger></FormControl>
              <SelectContent>
                <div className="px-2 pb-2">
                  <Input
                    placeholder="搜索品牌..."
                    value={brandSearch}
                    onChange={(e) => setBrandSearch(e.target.value)}
                    className="h-8"
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.stopPropagation()}
                  />
                </div>
                {filteredBrands.length === 0
                  ? <div className="py-2 px-2 text-sm text-muted-foreground">无匹配品牌</div>
                  : filteredBrands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)
                }
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )} />

        {/* Question Set */}
        <FormField control={form.control} name="question_set_id" render={({ field }) => (
          <FormItem>
            <FormLabel>问题集 <span className="text-destructive">*</span></FormLabel>
            <div className="flex items-center gap-2">
              <Select onValueChange={field.onChange} value={field.value} disabled={!watchBrandId}>
                <FormControl><SelectTrigger className="flex-1"><SelectValue placeholder={watchBrandId ? "选择问题集" : "请先选择品牌"} /></SelectTrigger></FormControl>
                <SelectContent>
                  {filteredQSets.length === 0
                    ? <div className="py-2 px-2 text-sm text-muted-foreground">该品牌下无问题集</div>
                    : filteredQSets.map((qs) => <SelectItem key={qs.id} value={qs.id}>{qs.name}</SelectItem>)
                  }
                </SelectContent>
              </Select>
              <Button type="button" variant="outline" size="icon" className="shrink-0" disabled={!watchBrandId}
                onClick={() => onCreateQS(watchBrandId)} title="新建问题集">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <FormMessage />
          </FormItem>
        )} />

        {/* Category */}
        <FormField control={form.control} name="category" render={({ field }) => (
          <FormItem>
            <FormLabel>问题分类</FormLabel>
            <Select onValueChange={(v) => field.onChange(v === "__none__" ? "" : v)} value={field.value || "__none__"}>
              <FormControl><SelectTrigger><SelectValue placeholder="选择分类（可选）" /></SelectTrigger></FormControl>
              <SelectContent>
                <SelectItem value="__none__">不指定分类</SelectItem>
                {QUESTION_CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )} />

        {/* Content */}
        <FormField control={form.control} name="content" render={({ field }) => (
          <FormItem>
            <FormLabel>问题内容 <span className="text-destructive">*</span></FormLabel>
            <FormControl>
              <Textarea placeholder="请输入问题内容..." rows={4} maxLength={500} {...field} />
            </FormControl>
            <div className="flex justify-between">
              <FormMessage />
              <span className={`text-xs ${contentLength > 450 ? "text-destructive" : "text-muted-foreground"}`}>
                {contentLength}/500
              </span>
            </div>
          </FormItem>
        )} />

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose}>取消</Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "创建中..." : "创建"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

// ============================================================
// Batch Create Form (Excel upload)
// ============================================================
function BatchCreateForm({
  brands, questionSets, selectedQS, onCreated, onClose,
}: {
  brands: Brand[];
  questionSets: QuestionSet[];
  selectedQS: QuestionSet | null;
  onCreated: () => void;
  onClose: () => void;
}) {
  const [brandId, setBrandId] = useState(selectedQS?.brand_id || "");
  const [qsId, setQsId] = useState(selectedQS?.id || "");
  const [uploading, setUploading] = useState(false);
  const [parsedQuestions, setParsedQuestions] = useState<{ content: string; category: string }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredQSets = useMemo(
    () => questionSets.filter((qs) => qs.brand_id === brandId),
    [questionSets, brandId]
  );

  const handleDownloadTemplate = () => {
    const header = "问题内容,问题分类\n";
    const example =
      "该品牌的核心竞争优势是什么？,品牌提及推荐\n" +
      "该品牌在同类产品中排名如何？,品牌排行\n" +
      "用户对该品牌的整体评价如何？,品牌用户情感\n";
    const blob = new Blob(["\uFEFF" + header + example], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "问题批量导入模板.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (!text) return;
      const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
      const first = lines[0].toLowerCase();
      const hasHeader = first.includes("问题") || first.includes("content") || first.includes("分类");
      const dataLines = hasHeader ? lines.slice(1) : lines;
      const parsed = dataLines.map((line) => {
        const sep = line.includes("\t") ? "\t" : ",";
        const parts = line.split(sep).map((p) => p.replace(/^["']|["']$/g, "").trim());
        return { content: parts[0] || "", category: parts[1] || "" };
      }).filter((q) => q.content);
      setParsedQuestions(parsed);
      toast.info(`已解析 ${parsed.length} 条问题`);
    };
    reader.readAsText(file, "utf-8");
    e.target.value = "";
  };

  const handleConfirmImport = async () => {
    if (!qsId || parsedQuestions.length === 0) return;
    setUploading(true);
    try {
      await questionApi.batchCreate({ question_set_id: qsId, questions: parsedQuestions });
      toast.success(`已导入 ${parsedQuestions.length} 条问题`);
      setParsedQuestions([]);
      onCreated();
      onClose();
    } catch {
      toast.error("导入失败");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Brand */}
      <div className="space-y-2">
        <label className="text-sm font-medium">品牌 <span className="text-destructive">*</span></label>
        <Select value={brandId} onValueChange={(v) => { setBrandId(v); setQsId(""); }}>
          <SelectTrigger><SelectValue placeholder="选择品牌" /></SelectTrigger>
          <SelectContent>
            {brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Question Set */}
      <div className="space-y-2">
        <label className="text-sm font-medium">问题集 <span className="text-destructive">*</span></label>
        <Select value={qsId} onValueChange={setQsId} disabled={!brandId}>
          <SelectTrigger><SelectValue placeholder={brandId ? "选择问题集" : "请先选择品牌"} /></SelectTrigger>
          <SelectContent>
            {filteredQSets.map((qs) => <SelectItem key={qs.id} value={qs.id}>{qs.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Template & Upload */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={handleDownloadTemplate}>
            <Download className="mr-2 h-4 w-4" />
            下载模板
          </Button>
          <input ref={fileInputRef} type="file" accept=".csv,.tsv,.txt,.xls,.xlsx" className="hidden" onChange={handleFileUpload} />
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
            <FileUp className="mr-2 h-4 w-4" />
            上传文件
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          支持 CSV/Excel 格式，第一列为问题内容（必填），第二列为问题分类（可选：品牌提及推荐、品牌排行、品牌用户情感）
        </p>
      </div>

      {/* Preview */}
      {parsedQuestions.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Badge variant="secondary">已解析 {parsedQuestions.length} 条问题</Badge>
            <Button variant="ghost" size="sm" onClick={() => setParsedQuestions([])}>
              <X className="mr-1 h-3.5 w-3.5" />清除
            </Button>
          </div>
          <div className="max-h-60 overflow-y-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0">
                <tr>
                  <th className="px-3 py-1.5 text-left font-medium w-8">#</th>
                  <th className="px-3 py-1.5 text-left font-medium">问题内容</th>
                  <th className="px-3 py-1.5 text-left font-medium w-28">分类</th>
                </tr>
              </thead>
              <tbody>
                {parsedQuestions.slice(0, 50).map((q, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-3 py-1.5 text-muted-foreground">{i + 1}</td>
                    <td className="px-3 py-1.5">{q.content}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{q.category || "-"}</td>
                  </tr>
                ))}
                {parsedQuestions.length > 50 && (
                  <tr className="border-t">
                    <td colSpan={3} className="px-3 py-1.5 text-center text-muted-foreground">
                      ... 还有 {parsedQuestions.length - 50} 条
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button onClick={handleConfirmImport} disabled={!qsId || parsedQuestions.length === 0 || uploading}>
          {uploading ? "导入中..." : `确认导入${parsedQuestions.length > 0 ? ` (${parsedQuestions.length}条)` : ""}`}
        </Button>
      </div>
    </div>
  );
}

// ============================================================
// AI Generate Form (inside drawer)
// ============================================================
function AIGenerateForm({
  brands, questionSets, selectedQS, brandNameMap, onCreated, onClose,
}: {
  brands: Brand[];
  questionSets: QuestionSet[];
  selectedQS: QuestionSet | null;
  brandNameMap: Record<string, string>;
  onCreated: () => void;
  onClose: () => void;
}) {
  const [brandId, setBrandId] = useState(selectedQS?.brand_id || "");
  const [qsId, setQsId] = useState(selectedQS?.id || "");
  const [category, setCategory] = useState("");
  const [generating, setGenerating] = useState(false);
  const [candidates, setCandidates] = useState<{ content: string; category: string }[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const filteredQSets = useMemo(
    () => questionSets.filter((qs) => qs.brand_id === brandId),
    [questionSets, brandId]
  );

  const brandName = brandNameMap[brandId] || "";

  const handleGenerate = () => {
    if (!brandName) {
      toast.error("请先选择品牌");
      return;
    }
    setGenerating(true);
    // Template-based generation (to be replaced with LLM API)
    setTimeout(() => {
      const categoryTemplates: Record<string, string[]> = {
        "品牌提及推荐": [
          `在${brandName}所在领域，AI 助手会推荐哪些品牌？`,
          `${brandName}是否出现在 AI 搜索结果的推荐列表中？`,
          `用户询问相关产品推荐时，${brandName}被提及的频率如何？`,
          `ChatGPT/文心一言 对${brandName}的推荐语是什么？`,
          `与竞品相比，${brandName}在 AI 推荐中的排名如何？`,
          `${brandName}在不同 AI 平台中的推荐一致性如何？`,
        ],
        "品牌排行": [
          `${brandName}在行业排名中处于什么位置？`,
          `AI 搜索引擎如何给${brandName}的行业排名？`,
          `${brandName}在同品类产品中的综合评分是多少？`,
          `与主要竞争对手相比，${brandName}的市场份额如何？`,
          `${brandName}在不同维度（质量、价格、服务）的排名分别如何？`,
          `${brandName}近期的排名变化趋势是什么？`,
        ],
        "品牌用户情感": [
          `用户对${brandName}的整体满意度如何？`,
          `${brandName}的产品口碑在社交媒体上是正面还是负面？`,
          `用户最常用哪些词汇来描述${brandName}？`,
          `${brandName}最近是否有负面舆情事件？`,
          `用户对${brandName}的忠诚度和复购意愿如何？`,
          `${brandName}的售后服务评价如何？`,
        ],
      };

      let results: { content: string; category: string }[] = [];
      if (category && categoryTemplates[category]) {
        results = categoryTemplates[category].map((content) => ({ content, category }));
      } else {
        // Generate from all categories
        for (const [cat, templates] of Object.entries(categoryTemplates)) {
          const picked = templates.sort(() => Math.random() - 0.5).slice(0, 2);
          results.push(...picked.map((content) => ({ content, category: cat })));
        }
      }
      results = results.sort(() => Math.random() - 0.5);
      setCandidates(results);
      setSelected(new Set(results.map((_, i) => i)));
      setGenerating(false);
    }, 1200);
  };

  const toggleSelect = (i: number) => {
    const next = new Set(selected);
    if (next.has(i)) next.delete(i); else next.add(i);
    setSelected(next);
  };

  const handleConfirmAdd = async () => {
    if (!qsId) { toast.error("请选择问题集"); return; }
    const toAdd = candidates.filter((_, i) => selected.has(i));
    if (toAdd.length === 0) return;
    try {
      await questionApi.batchCreate({ question_set_id: qsId, questions: toAdd });
      toast.success(`已添加 ${toAdd.length} 条问题`);
      setCandidates([]);
      setSelected(new Set());
      onCreated();
      onClose();
    } catch {
      toast.error("添加失败");
    }
  };

  return (
    <div className="space-y-5">
      {/* Brand */}
      <div className="space-y-2">
        <label className="text-sm font-medium">品牌 <span className="text-destructive">*</span></label>
        <Select value={brandId} onValueChange={(v) => { setBrandId(v); setQsId(""); setCandidates([]); }}>
          <SelectTrigger><SelectValue placeholder="选择品牌" /></SelectTrigger>
          <SelectContent>
            {brands.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Question Set */}
      <div className="space-y-2">
        <label className="text-sm font-medium">问题集 <span className="text-destructive">*</span></label>
        <Select value={qsId} onValueChange={setQsId} disabled={!brandId}>
          <SelectTrigger><SelectValue placeholder={brandId ? "选择问题集" : "请先选择品牌"} /></SelectTrigger>
          <SelectContent>
            {filteredQSets.map((qs) => <SelectItem key={qs.id} value={qs.id}>{qs.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Category filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium">问题分类方向</label>
        <Select value={category || "__all__"} onValueChange={(v) => setCategory(v === "__all__" ? "" : v)}>
          <SelectTrigger><SelectValue placeholder="全部分类" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部分类</SelectItem>
            {QUESTION_CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Generate button */}
      <Button onClick={handleGenerate} disabled={generating || !brandId} className="w-full">
        <Sparkles className="mr-2 h-4 w-4" />
        {generating ? "生成中..." : "根据品牌和分类生成问题"}
      </Button>

      <p className="text-xs text-muted-foreground">
        根据品牌「{brandName || "..."}」的信息和问题分类要求，AI 将自动生成候选问题。您可以采纳或修改后添加到问题集。
      </p>

      {/* Candidates */}
      {candidates.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Badge variant="secondary">已选 {selected.size}/{candidates.length}</Badge>
            <Button variant="ghost" size="sm" onClick={() => {
              setSelected(selected.size === candidates.length ? new Set() : new Set(candidates.map((_, i) => i)));
            }}>
              {selected.size === candidates.length ? "取消全选" : "全选"}
            </Button>
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {candidates.map((q, i) => (
              <label
                key={i}
                className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2 transition-colors ${
                  selected.has(i) ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(i)}
                  onChange={() => toggleSelect(i)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300"
                />
                <div className="flex-1">
                  <span className="text-sm">{q.content}</span>
                  {q.category && <Badge variant="outline" className="ml-2 text-xs">{q.category}</Badge>}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {candidates.length > 0 && (
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={() => setCandidates([])}>重新生成</Button>
          <Button onClick={handleConfirmAdd} disabled={selected.size === 0 || !qsId}>
            <Check className="mr-1 h-4 w-4" />
            采纳选中 ({selected.size})
          </Button>
        </div>
      )}
    </div>
  );
}
