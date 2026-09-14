import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ExecutionLog,
  ExecutionSummary,
  ImportSummary,
  PaginatedResponse,
  Route,
  RouteFilters,
} from '../models/route.models';

@Injectable({ providedIn: 'root' })
export class RoutesApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/routes`;

  getRoutes(filters: RouteFilters): Observable<PaginatedResponse<Route>> {
    let params = new HttpParams()
      .set('page', filters.page)
      .set('page_size', filters.pageSize);

    if (filters.status) params = params.set('status', filters.status);
    if (filters.priority) params = params.set('priority', filters.priority);
    if (filters.originOffice) params = params.set('origin_office', filters.originOffice);
    if (filters.search) params = params.set('search', filters.search.trim());
    if (filters.ordering) params = params.set('ordering', filters.ordering);
    if (filters.registeredFrom) {
      params = params.set('registered_from', `${filters.registeredFrom}T00:00:00-05:00`);
    }
    if (filters.registeredTo) {
      params = params.set('registered_to', `${filters.registeredTo}T23:59:59-05:00`);
    }

    return this.http.get<PaginatedResponse<Route>>(`${this.baseUrl}/`, { params });
  }

  getRoute(routeId: number): Observable<Route> {
    return this.http.get<Route>(`${this.baseUrl}/${routeId}/`);
  }

  getLogs(routeId: number): Observable<PaginatedResponse<ExecutionLog>> {
    return this.http.get<PaginatedResponse<ExecutionLog>>(`${this.baseUrl}/${routeId}/logs/`);
  }

  importWorkbook(file: File): Observable<ImportSummary> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportSummary>(`${this.baseUrl}/import/`, formData);
  }

  executeRoutes(routeIds: number[]): Observable<ExecutionSummary> {
    return this.http.post<ExecutionSummary>(`${this.baseUrl}/execute/`, {
      route_ids: routeIds,
    });
  }
}
