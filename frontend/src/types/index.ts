// --- Auth ---
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

// --- Brand ---
export interface Brand {
  id: string;
  name: string;
  industry: string;
  target_audience: string;
  selling_points: string;
  price_range: string;
  description: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface BrandCreate {
  name: string;
  industry?: string;
  target_audience?: string;
  selling_points?: string;
  price_range?: string;
  description?: string;
}

// --- Question ---
export interface QuestionSet {
  id: string;
  brand_id: string;
  name: string;
  description: string;
  question_count: number;
  created_by: string;
  created_at: string;
}

export interface Question {
  id: string;
  question_set_id: string;
  content: string;
  category: string;
  sort_order: number;
  created_at: string;
}

// --- Task ---
export interface Task {
  id: string;
  name: string;
  brand_id: string;
  question_set_id: string;
  task_type: string;
  status: string;
  model_scene: string;
  provider_type: string;
  config: Record<string, unknown>;
  progress: number;
  total_questions: number;
  completed_questions: number;
  created_by: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface TaskResult {
  id: string;
  task_id: string;
  question_id: string;
  model_name: string;
  model_version: string;
  question_text: string;
  answer_text: string;
  sources: unknown[];
  provider_type: string;
  source_type: string;
  ai_read_sources: string[];
  response_time_ms: number;
  created_at: string;
}

// --- Crawled Page ---
export interface CrawledPage {
  id: string;
  task_result_id: string;
  url: string;
  title: string;
  text_content: string;
  word_count: number;
  crawl_success: boolean;
  crawl_error: string | null;
  crawled_at: string;
}

// --- Browser Session ---
export interface BrowserSession {
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
