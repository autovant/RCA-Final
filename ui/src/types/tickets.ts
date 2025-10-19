export type TicketPlatform = 'servicenow' | 'jira';

export type TicketStatus = 
  | 'New' 
  | 'In Progress' 
  | 'On Hold' 
  | 'Resolved' 
  | 'Closed' 
  | 'Cancelled'
  | 'dry-run'
  | 'created'
  | 'pending';

export interface TicketMetadata {
  sys_id?: string;
  number?: string;
  state?: string;
  state_label?: string;
  id?: string;
  key?: string;
  self?: string;
  linked_servicenow?: {
    ticket_id: string;
    url?: string;
  };
  error?: string;
  dry_run_reason?: string;
  persisted_at?: string;
  sync?: {
    raw: unknown;
    refreshed_at: string;
  };
  labels?: string[];
  servicenow_incident_id?: string;
  assignment_group?: string;
  assigned_to?: string;
  configuration_item?: string;
  category?: string;
  subcategory?: string;
  priority?: string;
  [key: string]: unknown;
}

export interface Ticket {
  id: string;
  job_id: string;
  platform: TicketPlatform;
  ticket_id: string;
  url?: string;
  status: TicketStatus;
  profile_name?: string;
  dry_run: boolean;
  payload: Record<string, unknown>;
  metadata: TicketMetadata;
  created_at?: string;
  updated_at?: string;
}

export interface TicketListResponse {
  job_id: string;
  tickets: Ticket[];
}

export interface TicketCreateRequest {
  job_id: string;
  platform: TicketPlatform;
  payload?: Record<string, unknown>;
  profile_name?: string;
  dry_run?: boolean;
  ticket_id?: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface TicketDispatchRequest {
  job_id: string;
  payloads?: {
    servicenow?: Record<string, unknown>;
    jira?: Record<string, unknown>;
  };
  profile_name?: string;
  dry_run?: boolean;
}

export interface TicketToggleState {
  servicenow_enabled: boolean;
  jira_enabled: boolean;
  dual_mode: boolean;
}

export interface TicketToggleUpdateRequest {
  servicenow_enabled?: boolean;
  jira_enabled?: boolean;
  dual_mode?: boolean;
}

export interface ServiceNowPayload {
  short_description?: string;
  description?: string;
  assignment_group?: string;
  configuration_item?: string;
  assigned_to?: string;
  category?: string;
  subcategory?: string;
  priority?: string;
  state?: string;
  [key: string]: unknown;
}

export interface JiraPayload {
  project_key?: string;
  issue_type?: string;
  summary?: string;
  description?: string;
  assignee?: string | { name: string };
  labels?: string[];
  priority?: string | { name: string };
  components?: Array<{ name: string }>;
  custom_fields?: Record<string, unknown>;
  issue_links?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

// Template-related types
export interface TemplateMetadata {
  name: string;
  platform: TicketPlatform;
  description?: string;
  required_variables: string[];
  field_count: number;
}

export interface TemplateListResponse {
  templates: TemplateMetadata[];
  count: number;
}

export interface CreateFromTemplateRequest {
  job_id: string;
  platform: TicketPlatform;
  template_name: string;
  variables?: Record<string, unknown>;
  profile_name?: string;
  dry_run?: boolean;
}

export interface CreateFromTemplateResponse extends Ticket {
  template_name: string;
}
