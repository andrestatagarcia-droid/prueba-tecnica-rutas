import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { forkJoin, finalize } from 'rxjs';

import {
  ExecutionLog,
  ExecutionSummary,
  Route,
  RouteFilters,
} from './core/models/route.models';
import { RoutesApiService } from './core/services/routes-api.service';
import { apiErrorMessage } from './core/utils/api-error';
import { ImportPanelComponent } from './features/import-panel/import-panel.component';
import { RouteDetailComponent } from './features/route-detail/route-detail.component';
import { RouteFiltersComponent } from './features/route-filters/route-filters.component';
import { RouteTableComponent } from './features/route-table/route-table.component';

const INITIAL_FILTERS: RouteFilters = {
  status: '',
  priority: '',
  originOffice: '',
  registeredFrom: '',
  registeredTo: '',
  search: '',
  ordering: '-created_at',
  page: 1,
  pageSize: 25,
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    ImportPanelComponent,
    RouteDetailComponent,
    RouteFiltersComponent,
    RouteTableComponent,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  private readonly api = inject(RoutesApiService);

  readonly routes = signal<Route[]>([]);
  readonly filters = signal<RouteFilters>({ ...INITIAL_FILTERS });
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly executing = signal(false);
  readonly error = signal('');
  readonly selectedIds = signal<ReadonlySet<number>>(new Set<number>());
  readonly selectedCount = computed(() => this.selectedIds().size);
  readonly executionSummary = signal<ExecutionSummary | null>(null);

  readonly detailOpen = signal(false);
  readonly detailLoading = signal(false);
  readonly detailRoute = signal<Route | null>(null);
  readonly detailLogs = signal<ExecutionLog[]>([]);

  ngOnInit(): void {
    this.loadRoutes();
  }

  applyFilters(filters: RouteFilters): void {
    this.filters.set(filters);
    this.selectedIds.set(new Set<number>());
    this.loadRoutes();
  }

  changePage(page: number): void {
    this.filters.update((current) => ({ ...current, page }));
    this.loadRoutes();
  }

  refreshAfterImport(): void {
    this.filters.update((current) => ({ ...current, page: 1 }));
    this.selectedIds.set(new Set<number>());
    this.loadRoutes();
  }

  toggleRoute(routeId: number): void {
    const next = new Set(this.selectedIds());
    if (next.has(routeId)) next.delete(routeId);
    else next.add(routeId);
    this.selectedIds.set(next);
  }

  togglePageSelection(event: { ids: number[]; selected: boolean }): void {
    const next = new Set(this.selectedIds());
    for (const routeId of event.ids) {
      if (event.selected) next.add(routeId);
      else next.delete(routeId);
    }
    this.selectedIds.set(next);
  }

  executeSelection(): void {
    const routeIds = [...this.selectedIds()];
    if (routeIds.length === 0 || this.executing()) return;
    if (!window.confirm(`¿Deseas ejecutar ${routeIds.length} ruta(s) seleccionada(s)?`)) return;

    this.executing.set(true);
    this.error.set('');
    this.executionSummary.set(null);
    this.api
      .executeRoutes(routeIds)
      .pipe(finalize(() => this.executing.set(false)))
      .subscribe({
        next: (summary) => {
          this.executionSummary.set(summary);
          this.selectedIds.set(new Set<number>());
          this.loadRoutes();
        },
        error: (error: unknown) => this.error.set(apiErrorMessage(error)),
      });
  }

  openDetail(routeId: number): void {
    this.detailOpen.set(true);
    this.detailLoading.set(true);
    this.detailRoute.set(null);
    this.detailLogs.set([]);
    forkJoin({
      route: this.api.getRoute(routeId),
      logs: this.api.getLogs(routeId),
    })
      .pipe(finalize(() => this.detailLoading.set(false)))
      .subscribe({
        next: ({ route, logs }) => {
          this.detailRoute.set(route);
          this.detailLogs.set(logs.results);
        },
        error: (error: unknown) => {
          this.error.set(apiErrorMessage(error));
          this.detailOpen.set(false);
        },
      });
  }

  closeDetail(): void {
    this.detailOpen.set(false);
    this.detailRoute.set(null);
    this.detailLogs.set([]);
  }

  dismissExecutionSummary(): void {
    this.executionSummary.set(null);
  }

  private loadRoutes(): void {
    this.loading.set(true);
    this.error.set('');
    this.api
      .getRoutes(this.filters())
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (page) => {
          this.routes.set(page.results);
          this.total.set(page.count);
        },
        error: (error: unknown) => {
          this.routes.set([]);
          this.total.set(0);
          this.error.set(apiErrorMessage(error));
        },
      });
  }
}
