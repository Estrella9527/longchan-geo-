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
  created_at: string;
}
