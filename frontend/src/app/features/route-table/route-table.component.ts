import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { Route } from '../../core/models/route.models';

@Component({
  selector: 'app-route-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './route-table.component.html',
  styleUrl: './route-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RouteTableComponent {
  @Input({ required: true }) routes: Route[] = [];
  @Input({ required: true }) selectedIds: ReadonlySet<number> = new Set<number>();
  @Input() loading = false;
  @Input() total = 0;
  @Input() page = 1;
  @Input() pageSize = 25;

  @Output() readonly routeToggle = new EventEmitter<number>();
  @Output() readonly pageToggle = new EventEmitter<{ ids: number[]; selected: boolean }>();
  @Output() readonly detail = new EventEmitter<number>();
  @Output() readonly pageChange = new EventEmitter<number>();

  get readyRoutes(): Route[] {
    return this.routes.filter((route) => route.status === 'READY');
  }

  get allReadySelected(): boolean {
    return this.readyRoutes.length > 0 && this.readyRoutes.every((route) => this.selectedIds.has(route.id));
  }

  get firstRow(): number {
    return this.total === 0 ? 0 : (this.page - 1) * this.pageSize + 1;
  }

  get lastRow(): number {
    return Math.min(this.page * this.pageSize, this.total);
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  toggleCurrentPage(): void {
    this.pageToggle.emit({
      ids: this.readyRoutes.map((route) => route.id),
      selected: !this.allReadySelected,
    });
  }

  statusLabel(status: Route['status']): string {
    const labels: Record<Route['status'], string> = {
      PENDING: 'Pendiente',
      READY: 'Lista',
      EXECUTED: 'Ejecutada',
      FAILED: 'Fallida',
    };
    return labels[status];
  }
}
