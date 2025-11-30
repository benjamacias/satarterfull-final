import { Component } from '@angular/core';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-cpe-consulta',
  standalone: false,
  templateUrl: './cpe-consulta.component.html'
})
export class CpeConsultaComponent {
  nro_ctg = '';
  pesoDescarga: number | null = null;
  resultado: any = null;
  loading = false;
  lastQuery = '';
  descargandoPdf = false;

  constructor(private api: ApiService) {}

  buscar() {
    if (!this.nro_ctg || this.loading) {
      return;
    }
    this.loading = true;
    this.lastQuery = this.nro_ctg;
    this.api.consultarCPE(this.nro_ctg, this.pesoDescarga).subscribe({
      next: r => {
        this.resultado = r;
        this.loading = false;
      },
      error: _ => {
        this.loading = false;
        alert('Error consultando CPE');
      }
    });
  }

  descargarPdf(): void {
    if (!this.resultado?.id || this.descargandoPdf) {
      return;
    }

    this.descargandoPdf = true;
    this.api.descargarPdfCpe(this.resultado.id).subscribe({
      next: blob => {
        const url = window.URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `cpe-${this.resultado.nro_ctg || 'documento'}.pdf`;
        enlace.click();
        window.URL.revokeObjectURL(url);
        this.descargandoPdf = false;
      },
      error: _ => {
        this.descargandoPdf = false;
        alert('No se pudo descargar el PDF de la carta de porte.');
      }
    });
  }

  estadoBadge(value: string | null | undefined): 'success' | 'warning' | 'info' {
    if (!value) {
      return 'info';
    }
    const normalized = value.toLowerCase();
    if (normalized.includes('vig') || normalized.includes('activo')) {
      return 'success';
    }
    if (normalized.includes('pend')) {
      return 'warning';
    }
    return 'info';
  }
}
