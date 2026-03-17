import axios from "axios";
import type {
  Brand,
  BrandCreate,
  QuestionSet,
  Question,
  Task,
  TaskResult,
  CrawledPage,
  UserInfo,
  BrowserSession,
} from "@/types";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  me: () => api.get<UserInfo>("/auth/me"),
  initAdmin: () => api.post<UserInfo>("/auth/init-admin"),
};

// --- Brands ---
export const brandApi = {
  list: (params?: { keyword?: string; page?: number; page_size?: number }) =>
    api.get<Brand[]>("/brands", { params }),
  get: (id: string) => api.get<Brand>(`/brands/${id}`),
  create: (data: BrandCreate) => api.post<Brand>("/brands", data),
  update: (id: string, data: Partial<BrandCreate>) =>
    api.put<Brand>(`/brands/${id}`, data),
  delete: (id: string) => api.delete(`/brands/${id}`),
};

// --- Question Sets ---
export const questionSetApi = {
  list: (params?: { brand_id?: string }) =>
    api.get<QuestionSet[]>("/questions/sets", { params }),
  create: (data: { brand_id: string; name: string; description?: string }) =>
    api.post<QuestionSet>("/questions/sets", data),
  update: (id: string, data: { name?: string; description?: string }) =>
    api.put<QuestionSet>(`/questions/sets/${id}`, data),
  delete: (id: string) => api.delete(`/questions/sets/${id}`),
};

// --- Questions ---
export const questionApi = {
  list: (questionSetId: string) =>
    api.get<Question[]>("/questions", { params: { question_set_id: questionSetId } }),
  create: (data: { question_set_id: string; content: string; category?: string }) =>
    api.post<Question>("/questions", data),
  update: (id: string, data: { content?: string; category?: string }) =>
    api.put<Question>(`/questions/${id}`, data),
  batchCreate: (data: { question_set_id: string; questions: { content: string; category?: string }[] }) =>
    api.post<Question[]>("/questions/batch", data),
  reorder: (data: { question_ids: string[] }) =>
    api.put("/questions/reorder", data),
  delete: (id: string) => api.delete(`/questions/${id}`),
};

// --- Tasks ---
export const taskApi = {
  list: (params?: { brand_id?: string; task_status?: string; page?: number; page_size?: number }) =>
    api.get<Task[]>("/tasks", { params }),
  get: (id: string) => api.get<Task>(`/tasks/${id}`),
  create: (data: { name: string; brand_id: string; question_set_id: string; task_type?: string; model_scene?: string; provider_type?: string; config?: Record<string, unknown> }) =>
    api.post<Task>("/tasks", data),
  start: (id: string) => api.post<Task>(`/tasks/${id}/start`),
  pause: (id: string) => api.post<Task>(`/tasks/${id}/pause`),
  cancel: (id: string) => api.post<Task>(`/tasks/${id}/cancel`),
  delete: (id: string) => api.delete(`/tasks/${id}`),
  results: (id: string, params?: { page?: number; page_size?: number }) =>
    api.get<TaskResult[]>(`/tasks/${id}/results`, { params }),
  crawledPages: (resultId: string) =>
    api.get<CrawledPage[]>(`/tasks/results/${resultId}/crawled-pages`),
};

// --- Browser Sessions ---
export const sessionApi = {
  list: () => api.get<BrowserSession[]>("/sessions").then((r) => r.data),
  create: (data: { provider_name: string; display_name: string; phone_number?: string }) =>
    api.post<BrowserSession>("/sessions", data),
  activate: (id: string) => api.post(`/sessions/${id}/activate`),
  healthCheck: (id: string) => api.post(`/sessions/${id}/health-check`),
  delete: (id: string) => api.delete(`/sessions/${id}`),
  authStart: (id: string, phone: string) =>
    api.post(`/sessions/${id}/auth/start`, { phone_number: phone }),
  authStatus: (id: string) =>
    api.get<{ state: string; message?: string; screenshot?: string; captcha_type?: string; captcha_instruction?: string }>(`/sessions/${id}/auth/status`).then((r) => r.data),
  authCode: (id: string, code: string) =>
    api.post(`/sessions/${id}/auth/code`, { code }),
  captchaData: (id: string) =>
    api.get<{ screenshot: string; instruction: string; captcha_type: string }>(
      `/sessions/${id}/auth/captcha`
    ).then((r) => r.data),
  captchaAction: (id: string, action: Record<string, unknown>) =>
    api.post(`/sessions/${id}/auth/captcha`, action),
};

// --- Analysis ---
export const analysisApi = {
  brand: (brandId: string, days: number = 30) =>
    api.get(`/analysis/brand/${brandId}`, { params: { days } }),
  competitor: (brandIds: string[]) =>
    api.get("/analysis/competitor", { params: { brand_ids: brandIds.join(",") } }),
  exportCsv: (taskId: string) =>
    api.get(`/analysis/export/${taskId}`, { responseType: "blob" }),
};

// --- Dashboard Stats ---
export interface DashboardStats {
  brand_count: number;
  question_set_count: number;
  running_tasks: number;
  completed_tasks: number;
  total_tasks: number;
}

export const statsApi = {
  dashboard: () => api.get<DashboardStats>("/stats/dashboard"),
};

export default api;
