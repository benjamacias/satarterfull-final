import { Component, OnInit } from '@angular/core';
import { ApiService, Client, EnvioFactura } from '../core/api.service';

@Component({
  selector: 'app-facturar',
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
  taxConditionOptions = [
    { value: 5, label: 'Consumidor Final' },
    { value: 4, label: 'Responsable Inscripto' },
    { value: 6, label: 'Monotributo' }
  ];
  loading = false;
  clientsLoading = false;
  resp: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
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

  emitir(): void {
    if (!this.model.client_id) {
      alert('Seleccioná un cliente antes de emitir.');
      return;
    }
    this.loading = true;
    this.api.emitirFactura(this.model).subscribe({
      next: r => {
        this.resp = r;
        this.loading = false;
      },
      error: _ => {
        this.loading = false;
        alert('Error emitiendo la factura. Verificá los datos ingresados.');
      }
    });
  }
}
