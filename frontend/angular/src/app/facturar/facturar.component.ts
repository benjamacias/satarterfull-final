import { Component, OnInit } from '@angular/core';
import {
  ApiService,
  Client,
  ComprobanteAsociado,
  EnvioFactura,
  PeriodoAsociado,
} from '../core/api.service';

type TipoComprobante = 'FACTURA' | 'NOTA_CREDITO' | 'NOTA_DEBITO';
type ModoAsociacion = 'none' | 'cbte' | 'periodo';

interface TipoComprobanteConfig {
  label: string;
  value: TipoComprobante;
  letras: { [letra: string]: number };
}

@Component({
  selector: 'app-facturar',
  standalone: false,
  templateUrl: './facturar.component.html'
})

export class FacturarComponent implements OnInit {
  model: EnvioFactura = {
    client_id: null,
    amount: 0,
    pto_vta: 1,
    cbte_tipo: 11,
    doc_tipo: 80,
    doc_nro: '',
    condicion_iva_receptor_id: 5
  };
  clients: Client[] = [];
  selectedClient: Client | null = null;
  tiposComprobante: TipoComprobanteConfig[] = [
    {
      value: 'FACTURA',
      label: 'Factura',
      letras: { A: 1, B: 6, C: 11 }
    },
    {
      value: 'NOTA_CREDITO',
      label: 'Nota de Crédito',
      letras: { A: 3, B: 8, C: 13 }
    },
    {
      value: 'NOTA_DEBITO',
      label: 'Nota de Débito',
      letras: { A: 2, B: 7, C: 12 }
    }
  ];
  tipoSeleccionado: TipoComprobante = 'FACTURA';
  letraSeleccionada = 'C';
  modoAsociacion: ModoAsociacion = 'none';
  comprobanteAsociado: Partial<ComprobanteAsociado> = {};
  periodoAsociado: Partial<PeriodoAsociado> = {};
  taxConditionOptions = [
    { value: 5, label: 'Consumidor Final' },
    { value: 4, label: 'Responsable Inscripto' },
    { value: 6, label: 'Monotributo' }
  ];
  loading = false;
  clientsLoading = false;
  resp: any = null;
  errors: string[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.actualizarCbteSegunSeleccion();
    this.clientsLoading = true;
    this.api.listarClientes().subscribe({
      next: clients => {
        this.clients = [...clients].sort((a, b) => a.name.localeCompare(b.name));
        this.clientsLoading = false;
      },
      error: _ => {
        this.clientsLoading = false;
        alert('No se pudieron obtener los clientes registrados.');
      }
    });
  }

  seleccionarCliente(id: number | null): void {
    if (!id) {
      this.selectedClient = null;
      this.model.client_id = null;
      this.model.doc_nro = '';
      this.model.condicion_iva_receptor_id = 5;
      return;
    }
    this.model.client_id = id;
    this.selectedClient = this.clients.find(c => c.id === id) ?? null;
    if (this.selectedClient) {
      this.model.doc_tipo = 80;
      this.model.doc_nro = this.selectedClient.tax_id;
      this.model.condicion_iva_receptor_id = this.selectedClient.tax_condition;
    }
  }

  actualizarCbteSegunSeleccion(): void {
    const config = this.tiposComprobante.find(t => t.value === this.tipoSeleccionado);
    if (!config) {
      return;
    }
    const letrasDisponibles = Object.keys(config.letras);
    if (!letrasDisponibles.includes(this.letraSeleccionada)) {
      this.letraSeleccionada = letrasDisponibles[0];
    }
    this.model.cbte_tipo = config.letras[this.letraSeleccionada];
    if (this.tipoSeleccionado === 'FACTURA') {
      this.modoAsociacion = 'none';
      this.comprobanteAsociado = {};
      this.periodoAsociado = {};
    } else if (this.modoAsociacion === 'none') {
      this.modoAsociacion = 'cbte';
    }
  }

  seleccionarTipo(value: TipoComprobante): void {
    this.tipoSeleccionado = value;
    this.letraSeleccionada = value === 'FACTURA' ? 'C' : 'A';
    this.actualizarCbteSegunSeleccion();
  }

  seleccionarLetra(letra: string): void {
    this.letraSeleccionada = letra;
    this.actualizarCbteSegunSeleccion();
  }

  seleccionarModoAsociacion(modo: ModoAsociacion): void {
    this.modoAsociacion = modo;
    if (modo !== 'cbte') {
      this.comprobanteAsociado = {};
    }
    if (modo !== 'periodo') {
      this.periodoAsociado = {};
    }
  }

  get letrasDisponibles(): string[] {
    const config = this.tiposComprobante.find(t => t.value === this.tipoSeleccionado);
    return config ? Object.keys(config.letras) : [];
  }

  get descripcionComprobante(): string {
    const config = this.tiposComprobante.find(t => t.value === this.tipoSeleccionado);
    if (!config) {
      return `${this.model.cbte_tipo}`;
    }
    return `${config.label} ${this.letraSeleccionada}`;
  }

  private buildPayload(): EnvioFactura {
    const payload: EnvioFactura = { ...this.model };
    delete (payload as any).cbtes_asoc;
    delete (payload as any).periodo_asoc;

    if (this.tipoSeleccionado !== 'FACTURA') {
      if (this.modoAsociacion === 'cbte') {
        const { tipo, pto_vta, nro, cuit, cbte_fch } = this.comprobanteAsociado;
        if (tipo != null && pto_vta != null && nro != null) {
          payload.cbtes_asoc = {
            tipo: Number(tipo),
            pto_vta: Number(pto_vta),
            nro: Number(nro),
            ...(cuit ? { cuit: String(cuit) } : {}),
            ...(cbte_fch ? { cbte_fch: String(cbte_fch) } : {})
          };
        }
      } else if (this.modoAsociacion === 'periodo') {
        const { desde, hasta } = this.periodoAsociado;
        if (desde && hasta) {
          payload.periodo_asoc = {
            desde: String(desde),
            hasta: String(hasta)
          };
        }
      }
    }

    return payload;
  }

  private validarDatos(): boolean {
    if (!this.model.client_id) {
      alert('Seleccioná un cliente antes de emitir.');
      return false;
    }

    if (this.tipoSeleccionado !== 'FACTURA') {
      if (this.modoAsociacion === 'cbte') {
        if (
          this.comprobanteAsociado.tipo == null ||
          this.comprobanteAsociado.pto_vta == null ||
          this.comprobanteAsociado.nro == null
        ) {
          alert('Completá los datos del comprobante asociado.');
          return false;
        }
      } else if (this.modoAsociacion === 'periodo') {
        if (!this.periodoAsociado.desde || !this.periodoAsociado.hasta) {
          alert('Indicá el período asociado (desde y hasta).');
          return false;
        }
      } else {
        alert('Seleccioná cómo querés asociar la nota (comprobante o período).');
        return false;
      }
    }

    return true;
  }

  emitir(): void {
    if (!this.validarDatos()) {
      return;
    }
    this.resp = null;
    this.loading = true;
    this.errors = [];
    this.api.emitirFactura(this.buildPayload()).subscribe({
      next: r => {
        this.resp = r;
        this.loading = false;
        this.errors = [];
      },
      error: err => {
        this.loading = false;
        this.errors = this.parseErrors(err);
        if (!this.errors.length) {
          alert('Error emitiendo la factura. Verificá los datos ingresados.');
        }
      }
    });
  }

  private parseErrors(err: any): string[] {
    const errors: string[] = [];
    const data = err?.error;
    if (!data) {
      return errors;
    }

    if (typeof data === 'string') {
      return [data];
    }

    if (Array.isArray(data)) {
      return data.map((item: any) => String(item));
    }

    if (typeof data === 'object') {
      for (const [field, messages] of Object.entries(data)) {
        if (Array.isArray(messages)) {
          messages.forEach(msg => errors.push(`${field}: ${msg}`));
        } else if (messages && typeof messages === 'object') {
          errors.push(`${field}: ${JSON.stringify(messages)}`);
        } else if (messages) {
          errors.push(`${field}: ${messages}`);
        }
      }
    }

    return errors;
  }
}
