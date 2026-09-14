import { ChangeDetectionStrategy, Component, EventEmitter, inject, Output, signal } from '@angular/core';
import { finalize } from 'rxjs';

import { ImportSummary } from '../../core/models/route.models';
import { RoutesApiService } from '../../core/services/routes-api.service';
import { apiErrorMessage } from '../../core/utils/api-error';

const MAX_FILE_SIZE = 15 * 1024 * 1024;

@Component({
  selector: 'app-import-panel',
  standalone: true,
  templateUrl: './import-panel.component.html',
  styleUrl: './import-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImportPanelComponent {
  @Output() readonly imported = new EventEmitter<void>();

  private readonly api = inject(RoutesApiService);
  readonly file = signal<File | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly summary = signal<ImportSummary | null>(null);

  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const selected = input.files?.[0] ?? null;
    this.error.set('');
    this.summary.set(null);

    if (!selected) {
      this.file.set(null);
      return;
    }
    if (!selected.name.toLowerCase().endsWith('.xlsx')) {
      this.file.set(null);
      this.error.set('Selecciona un archivo con extensión .xlsx.');
      input.value = '';
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      this.file.set(null);
      this.error.set('El archivo supera el límite de 15 MB.');
      input.value = '';
      return;
    }
    this.file.set(selected);
  }

  upload(): void {
    const selected = this.file();
    if (!selected || this.loading()) return;

    this.loading.set(true);
    this.error.set('');
    this.summary.set(null);
    this.api
      .importWorkbook(selected)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (summary) => {
          this.summary.set(summary);
          this.imported.emit();
        },
        error: (error: unknown) => this.error.set(apiErrorMessage(error)),
      });
  }
}
