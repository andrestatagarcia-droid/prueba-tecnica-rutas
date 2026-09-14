export type RouteStatus = 'PENDING' | 'READY' | 'EXECUTED' | 'FAILED';
export type ExecutionResult = 'SUCCESS' | 'ERROR' | 'NOT_FOUND';

export interface RoutePayload {
  point: number;
  point_city: string;
  address: string;
  latitude: string;
  longitude: string;
  first_piece_weight: string | null;
  raw_payload: Record<string, unknown>;
}

export interface Route {
  id: number;
  source_id: number | null;
  origin_office: number;
  origin_office_name: string;
  registered_at: string;
  origin: string;
  destination: string;
  distance_km: string;
  priority: number;
  priority_name: string;
  time_window_start: string;
  time_window_end: string;
  status: RouteStatus;
  created_at: string;
  payload: RoutePayload;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface RouteFilters {
  status: RouteStatus | '';
  priority: string;
  originOffice: string;
  registeredFrom: string;
  registeredTo: string;
  search: string;
  ordering: string;
  page: number;
  pageSize: number;
}

export interface ImportIssue {
  row: number;
  route_id: number | null;
  field: string;
  code: string;
  message: string;
  raw_value: unknown;
}

export interface ImportSummary {
  batch_id: string;
  status: string;
  total_rows: number;
  imported: number;
  rejected: number;
  error_count: number;
  errors: ImportIssue[];
  has_more_errors: boolean;
}

export interface ExecutionItem {
  route_id: number;
  result: ExecutionResult;
  status: RouteStatus | null;
  message: string;
}

export interface ExecutionSummary {
  requested: number;
  executed: number;
  failed: number;
  results: ExecutionItem[];
}

export interface ExecutionLog {
  id: number;
  route: number;
  execution_time: string;
  result: Exclude<ExecutionResult, 'NOT_FOUND'>;
  message: string;
}
