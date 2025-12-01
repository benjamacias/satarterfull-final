import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ApiService, DominioEstadistica, EstadisticasDominiosResponse } from '../core/api.service';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-vehiculos-dashboard',
  templateUrl: './vehiculos-dashboard.component.html',
  styleUrls: ['./vehiculos-dashboard.component.scss'],
  standalone: false
})
export class VehiculosDashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('movimientosChart') movimientosChart?: ElementRef<HTMLCanvasElement>;
  @ViewChild('totalesChart') totalesChart?: ElementRef<HTMLCanvasElement>;
  @ViewChild('facturacionChart') facturacionChart?: ElementRef<HTMLCanvasElement>;

  loading = false;
  error = '';
  stats: EstadisticasDominiosResponse | null = null;

  totalMovimientos = 0;
  totalFacturacion = 0;
  totalDominios = 0;

  private charts: Chart[] = [];
  private viewReady = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.cargarEstadisticas();
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderCharts();
  }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  recargar(): void {
    this.cargarEstadisticas();
  }

  private cargarEstadisticas(): void {
    this.loading = true;
    this.error = '';
    this.api.obtenerEstadisticasDominios().subscribe({
      next: (data) => {
        this.stats = this.normalizarDatos(data);
        this.calcularResumen();
        this.loading = false;
        setTimeout(() => this.renderCharts());
      },
      error: () => {
        this.loading = false;
        this.error = 'No pudimos obtener las estadísticas de dominios. Intentá nuevamente en unos minutos.';
      }
    });
  }

  private normalizarDatos(data: EstadisticasDominiosResponse): EstadisticasDominiosResponse {
    const normalizarLista = (lista: DominioEstadistica[]) =>
      lista.map((item) => ({
        ...item,
        movimientos: Number(item.movimientos) || 0,
        total_ctg: Number(item.total_ctg) || 0,
        facturacion: Number(item.facturacion) || 0
      }));

    return {
      mayores_movimientos: normalizarLista(data.mayores_movimientos || []),
      mayor_facturacion: normalizarLista(data.mayor_facturacion || [])
    };
  }

  private calcularResumen(): void {
    if (!this.stats) {
      this.totalMovimientos = 0;
      this.totalFacturacion = 0;
      this.totalDominios = 0;
      return;
    }
    const unicos = new Set<string>();
    this.totalMovimientos = 0;
    this.totalFacturacion = 0;

    const todas = [...this.stats.mayores_movimientos, ...this.stats.mayor_facturacion];
    todas.forEach((item) => {
      this.totalMovimientos += item.movimientos;
      this.totalFacturacion += item.facturacion;
      if (item.dominio) {
        unicos.add(item.dominio);
      }
    });
    this.totalDominios = unicos.size;
  }

  private renderCharts(): void {
    if (!this.viewReady || !this.stats) {
      return;
    }
    this.destroyCharts();

    const colores = ['#38bdf8', '#2563eb', '#7c3aed', '#22c55e', '#f59e0b', '#ef4444'];

    if (this.movimientosChart?.nativeElement) {
      const labels = this.stats.mayores_movimientos.map((item) => item.dominio || '—');
      const data = this.stats.mayores_movimientos.map((item) => item.movimientos);
      this.charts.push(
        new Chart(this.movimientosChart.nativeElement, {
          type: 'bar' as ChartType,
          data: {
            labels,
            datasets: [
              {
                label: 'Movimientos',
                data,
                backgroundColor: labels.map((_, idx) => colores[idx % colores.length])
              }
            ]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false }
            },
            scales: {
              x: { title: { display: true, text: 'Dominio' } },
              y: { title: { display: true, text: 'Cantidad' }, beginAtZero: true, ticks: { precision: 0 } }
            }
          } satisfies ChartConfiguration['options']
        })
      );
    }

    if (this.totalesChart?.nativeElement) {
      const labels = this.stats.mayores_movimientos.map((item) => item.dominio || '—');
      const data = this.stats.mayores_movimientos.map((item) => item.total_ctg);
      this.charts.push(
        new Chart(this.totalesChart.nativeElement, {
          type: 'doughnut' as ChartType,
          data: {
            labels,
            datasets: [
              {
                label: 'Total CTG',
                data,
                backgroundColor: labels.map((_, idx) => colores[idx % colores.length])
              }
            ]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { position: 'bottom' }
            }
          } satisfies ChartConfiguration['options']
        })
      );
    }

    if (this.facturacionChart?.nativeElement) {
      const labels = this.stats.mayor_facturacion.map((item) => item.dominio || '—');
      const data = this.stats.mayor_facturacion.map((item) => item.facturacion);
      this.charts.push(
        new Chart(this.facturacionChart.nativeElement, {
          type: 'bar' as ChartType,
          data: {
            labels,
            datasets: [
              {
                label: 'Facturación estimada',
                data,
                backgroundColor: labels.map((_, idx) => colores[(idx + 2) % colores.length])
              }
            ]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => `Facturación: $${(ctx.parsed.y as number || 0).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                }
              }
            },
            scales: {
              x: { title: { display: true, text: 'Dominio' } },
              y: { title: { display: true, text: 'Monto estimado ($)' }, beginAtZero: true }
            }
          } satisfies ChartConfiguration['options']
        })
      );
    }
  }

  private destroyCharts(): void {
    this.charts.forEach((chart) => chart.destroy());
    this.charts = [];
  }
}

