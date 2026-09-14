import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { RouteFilters } from '../../core/models/route.models';

@Component({
  selector: 'app-route-filters',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './route-filters.component.html',
  styleUrl: './route-filters.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RouteFiltersComponent {
  @Output() readonly filtersChange = new EventEmitter<RouteFilters>();

  model = this.emptyFilters();

  apply(): void {
    this.filtersChange.emit({ ...this.model, page: 1 });
  }

  clear(): void {
    this.model = this.emptyFilters();
    this.apply();
  }

  private emptyFilters(): RouteFilters {
    return {
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
  }
}
