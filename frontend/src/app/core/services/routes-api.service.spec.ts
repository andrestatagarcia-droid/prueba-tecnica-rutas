import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { RouteFilters } from '../models/route.models';
import { RoutesApiService } from './routes-api.service';

describe('RoutesApiService', () => {
  let service: RoutesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [RoutesApiService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(RoutesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('serializes route filters using the API contract', () => {
    const filters: RouteFilters = {
      status: 'READY',
      priority: '3',
      originOffice: '10',
      registeredFrom: '2026-09-01',
      registeredTo: '2026-09-12',
      search: 'Bogotá',
      ordering: '-distance_km',
      page: 2,
      pageSize: 50,
    };

    service.getRoutes(filters).subscribe();

    const request = http.expectOne((candidate) => candidate.url.endsWith('/routes/'));
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('status')).toBe('READY');
    expect(request.request.params.get('registered_from')).toBe('2026-09-01T00:00:00-05:00');
    expect(request.request.params.get('page_size')).toBe('50');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('posts selected route identifiers with the expected field name', () => {
    service.executeRoutes([10, 20]).subscribe();

    const request = http.expectOne((candidate) => candidate.url.endsWith('/routes/execute/'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ route_ids: [10, 20] });
    request.flush({ requested: 2, executed: 2, failed: 0, results: [] });
  });
});
