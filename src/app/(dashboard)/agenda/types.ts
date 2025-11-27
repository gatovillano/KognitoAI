export interface AgendaEvent {
  id: string;
  summary: string;
  description: string;
  location?: string;
  event_datetime_utc: string;
  event_datetime_local: string;
  user_timezone: string;
  team_shared?: boolean | string;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
  linked_profiles?: any[];
  attendees?: string[];
  external_attendees?: string[];
  status?: string;
  end_date?: string;
}

export interface TaskResponse {
  id: string;
  description: string;
  is_completed: boolean;
  due_date?: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
  account_id: string;
  workspace_id?: string;
  team_id?: string;
  linked_profiles?: any[];
  start_date?: string;
  status?: string;
}
