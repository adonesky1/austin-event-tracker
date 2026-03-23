export type CalendarStatus = {
  enabled: boolean;
  calendar_id: string;
  calendar_name: string;
  min_score: number;
  horizon_days: number;
  sync_hour: number;
  timezone: string;
  latest_run: null | {
    id: string;
    trigger: string;
    status: string;
    started_at: string;
    completed_at: string | null;
    window_start: string;
    window_end: string;
    selected_count: number;
    created_count: number;
    updated_count: number;
    deleted_count: number;
    error: string | null;
  };
};

export type CalendarPreview = {
  status: string;
  trigger: string;
  dry_run: boolean;
  window_start: string;
  window_end: string;
  selected_count: number;
  created_count: number;
  updated_count: number;
  deleted_count: number;
  selected_events: Array<{ id: string; title: string; score: number; start: string }>;
  error: string | null;
};

export type AdminProfile = {
  id: string;
  email: string;
  city: string;
  adults: Array<{ age: number }>;
  children: Array<{ age: number }>;
  preferred_neighborhoods: string[];
  max_distance_miles: number;
  preferred_days: string[];
  preferred_times: string[];
  budget: string;
  interests: string[];
  dislikes: string[];
  max_events_per_digest: number;
  crowd_sensitivity: string;
};

export type PromptConfig = {
  key: string;
  system_prompt: string;
  user_prompt_template: string;
  is_default: boolean;
  updated_at: string | null;
};

export type TrackedItem = {
  id: string;
  label: string;
  kind: "artist" | "venue" | "keyword" | "series";
  enabled: boolean;
  boost_weight: number;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type SourceRecord = {
  name: string;
  type: string;
  status: string;
  enabled: boolean;
};
