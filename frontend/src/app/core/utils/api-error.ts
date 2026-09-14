import { HttpErrorResponse } from '@angular/common/http';

export function apiErrorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return 'Ocurrió un error inesperado. Intenta nuevamente.';
  }

  const body: unknown = error.error;
  if (typeof body === 'string' && body.trim()) return body;
  if (isRecord(body)) {
    if (typeof body['message'] === 'string') return body['message'];
    const detail = firstMessage(body);
    if (detail) return detail;
  }

  if (error.status === 0) {
    return 'No fue posible conectar con la API. Verifica que el backend esté activo.';
  }
  return `La solicitud falló con estado HTTP ${error.status}.`;
}

function firstMessage(value: Record<string, unknown>): string | null {
  for (const [field, detail] of Object.entries(value)) {
    if (typeof detail === 'string') return `${field}: ${detail}`;
    if (Array.isArray(detail) && typeof detail[0] === 'string') {
      return `${field}: ${detail[0]}`;
    }
    if (isRecord(detail)) {
      const nested = firstMessage(detail);
      if (nested) return nested;
    }
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
