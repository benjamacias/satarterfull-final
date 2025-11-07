import { Component, OnInit } from '@angular/core';
import { ApiService, Client, CpeFacturaDetalle, EnvioFactura } from '../core/api.service';

interface CpeSeleccionable extends CpeFacturaDetalle {
  selected: boolean;
  editingTariff: number;
  updatingTariff: boolean;
}

@Component({
  selector: 'app-factura-cpe',
  templateUrl: './factura-cpe.component.html'
})
export class FacturaCpeComponent implements OnInit {
  clientes: Client[] = [];
  cpes: CpeSeleccionable[] = [];
  selectedClient: Client | null = null;
  loadingClientes = false;
  loadingCpes = false;
  facturando = false;
  respuesta: any = null;

  modeloFactura: EnvioFactura = {
    client_id: null,
    amount: 0,
    pto_vta: 1,
    cbte_tipo: 11,
    doc_tipo: 80,
    doc_nro: '',
    condicion_iva_receptor_id: 5
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.cargarClientes();
  }

  private cargarClientes(): void {
    this.loadingClientes = true;
    this.api.listarClientes().subscribe({
      next: clientes => {
        this.clientes = [...clientes].sort((a, b) => a.name.localeCompare(b.name));
        this.loadingClientes = false;
      },
      error: _ => {
        this.loadingClientes = false;
        alert('No se pudieron obtener los clientes registrados.');
      }
    });
  }

  seleccionarCliente(id: string | number | null): void {
    if (!id) {
      this.selectedClient = null;
      this.modeloFactura = {
        client_id: null,
        amount: 0,
        pto_vta: 1,
        cbte_tipo: 11,
        doc_tipo: 80,
        doc_nro: '',
        condicion_iva_receptor_id: 5
      };
      this.cpes = [];
      return;
    }
    const numericId = typeof id === 'string' ? parseInt(id, 10) : id;
    this.selectedClient = this.clientes.find(c => c.id === numericId) ?? null;
    if (this.selectedClient) {
      this.modeloFactura.client_id = this.selectedClient.id;
      this.modeloFactura.doc_tipo = 80;
      this.modeloFactura.doc_nro = this.selectedClient.tax_id;
      this.modeloFactura.condicion_iva_receptor_id = this.selectedClient.tax_condition;
    }
    this.cargarCpes(numericId);
  }

  private normalizarNumero(valor: number | string | null | undefined): number | null {
    if (valor === null || valor === undefined || valor === '') {
      return null;
    }
    const n = typeof valor === 'number' ? valor : parseFloat(valor);
    return isNaN(n) ? null : n;
  }

  private cargarCpes(clienteId: number): void {
    this.loadingCpes = true;
    this.api.listarCpePorCliente(clienteId).subscribe({
      next: datos => {
        this.cpes = datos.map(detalle => {
          const tarifa = this.normalizarNumero(detalle.tariff) ?? 0;
          return {
            ...detalle,
            peso_bruto_descarga: this.normalizarNumero(detalle.peso_bruto_descarga),
            tariff: tarifa,
            total_amount: this.normalizarNumero(detalle.total_amount),
            selected: false,
            editingTariff: tarifa,
            updatingTariff: false
          } as CpeSeleccionable;
        });
        this.loadingCpes = false;
        this.actualizarTotales();
      },
      error: _ => {
        this.loadingCpes = false;
        alert('No se pudieron obtener las cartas de porte del cliente seleccionado.');
      }
    });
  }

  alternarSeleccion(cpe: CpeSeleccionable, seleccionado: boolean): void {
    cpe.selected = seleccionado;
    this.actualizarTotales();
  }

  obtenerTotalCpe(cpe: CpeSeleccionable): number {
    if (cpe.total_amount !== null && cpe.total_amount !== undefined) {
      return cpe.total_amount;
    }
    const tarifa = cpe.tariff ?? 0;
    if (!cpe.peso_bruto_descarga) {
      return tarifa;
    }
    return tarifa * cpe.peso_bruto_descarga;
  }

  private actualizarTotales(): void {
    const total = this.cpes
      .filter(c => c.selected)
      .reduce((acum, c) => acum + this.obtenerTotalCpe(c), 0);
    this.modeloFactura.amount = parseFloat(total.toFixed(2));
  }

  guardarTarifa(cpe: CpeSeleccionable): void {
    const valor = this.normalizarNumero(cpe.editingTariff);
    if (valor === null) {
      alert('Ingresá un valor numérico válido para la tarifa.');
      return;
    }
    cpe.updatingTariff = true;
    this.api.actualizarTarifaCpe(cpe.id, valor).subscribe({
      next: actualizado => {
        cpe.updatingTariff = false;
        cpe.tariff = this.normalizarNumero(actualizado.tariff) ?? valor;
        cpe.total_amount = this.normalizarNumero(actualizado.total_amount);
        cpe.editingTariff = cpe.tariff ?? valor;
        this.actualizarTotales();
      },
      error: _ => {
        cpe.updatingTariff = false;
        alert('No se pudo actualizar la tarifa.');
      }
    });
  }

  emitirFactura(): void {
    if (!this.modeloFactura.client_id) {
      alert('Seleccioná un cliente y al menos una CPE antes de emitir.');
      return;
    }
    if (!this.cpes.some(c => c.selected)) {
      alert('Seleccioná al menos una carta de porte para calcular el importe de la factura.');
      return;
    }
    this.facturando = true;
    this.respuesta = null;
    const payload: EnvioFactura = { ...this.modeloFactura, amount: this.modeloFactura.amount };
    this.api.emitirFactura(payload).subscribe({
      next: resp => {
        this.facturando = false;
        this.respuesta = resp;
      },
      error: _ => {
        this.facturando = false;
        alert('Ocurrió un error al emitir la factura.');
      }
    });
  }
}
