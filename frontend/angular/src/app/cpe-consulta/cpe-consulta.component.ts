import { Component } from '@angular/core';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-cpe-consulta',
  standalone: false,
  templateUrl: './cpe-consulta.component.html'
})
export class CpeConsultaComponent {
  nro_ctg = '';
  resultado: any = null;
  loading = false;
  lastQuery = '';

  constructor(private api: ApiService) {}

  buscar() {
    if (!this.nro_ctg || this.loading) {
      return;
    }
    this.loading = true;
    this.lastQuery = this.nro_ctg;
    this.api.consultarCPE(this.nro_ctg).subscribe({
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
