import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ExecutionLog, Route } from '../../core/models/route.models';

@Component({
  selector: 'app-route-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './route-detail.component.html',
  styleUrl: './route-detail.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RouteDetailComponent {
  @Input() route: Route | null = null;
  @Input() logs: ExecutionLog[] = [];
  @Input() loading = false;
  @Output() readonly closed = new EventEmitter<void>();
}
