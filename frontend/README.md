# Frontend de operaciones logísticas

Aplicación standalone construida con Angular 22 para consumir la API Django de
rutas. No utiliza una librería visual externa; los componentes y estilos están
incluidos en el proyecto.

## Funcionalidades

- selección y carga de archivos `.xlsx` de hasta 15 MB;
- resumen de filas importadas, rechazadas y errores de validación;
- listado paginado de rutas;
- filtros por estado, prioridad, oficina y rango de fechas;
- búsqueda por origen, destino o dirección;
- ordenamiento por fecha, distancia o prioridad;
- selección exclusiva de rutas en estado `READY`;
- ejecución de hasta 100 rutas seleccionadas;
- detalle lateral con payload e historial de ejecución;
- estados de carga, errores de conectividad y confirmación de operaciones;
- diseño responsive y controles accesibles por teclado.

## Ejecución local

La API debe estar disponible en `http://localhost:8000/api/v1`.

```bash
npm install
npm start
```

Abrir `http://localhost:4200`.

Para cambiar la URL de la API, editar
`src/environments/environment.ts`.

## Verificación

```bash
npm test
npm run build
```

Las pruebas usan Vitest y `HttpTestingController` para verificar la construcción
de filtros y el contrato de ejecución masiva sin realizar llamadas reales.

## Componentes

| Componente | Responsabilidad |
|---|---|
| `ImportPanelComponent` | Selección, validación cliente, envío y reporte del workbook |
| `RouteFiltersComponent` | Captura y limpieza de criterios de consulta |
| `RouteTableComponent` | Tabla, paginación, selección y acceso al detalle |
| `RouteDetailComponent` | Datos operacionales, payload e historial de ejecución |
| `AppComponent` | Estado compartido y coordinación de los flujos |

La comunicación HTTP está centralizada en `RoutesApiService` y los contratos
TypeScript se encuentran en `core/models/route.models.ts`.
