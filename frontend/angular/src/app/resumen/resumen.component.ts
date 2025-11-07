import { Component, OnInit } from '@angular/core';
import { ApiService, Client, EnvioResumen, NuevoCliente } from '../core/api.service';

@Component({
  selector: 'app-resumen',
  templateUrl: './resumen.component.html'
})
export class ResumenComponent implements OnInit {
  clientes: Client[] = [];
  envios: EnvioResumen[] = [];
  loadingClientes = false;
  loadingEnvios = false;
  creandoCliente = false;
  mensajeCliente: string | null = null;
  nuevoCliente: NuevoCliente = this.defaultNuevoCliente();
  taxConditionOptions = [
    { value: 5, label: 'Consumidor Final' },
    { value: 4, label: 'Responsable Inscripto' },
    { value: 6, label: 'Monotributo' }
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.obtenerClientes();
    this.obtenerEnvios();
  }

  private obtenerClientes(): void {
    this.loadingClientes = true;
    this.api.listarClientes().subscribe({
      next: data => {
        this.clientes = [...data].sort((a, b) => a.name.localeCompare(b.name));
        this.loadingClientes = false;
      },
      error: _ => {
        this.loadingClientes = false;
        alert('No se pudieron cargar los clientes.');
      }
    });
  }

  private obtenerEnvios(): void {
    this.loadingEnvios = true;
    this.api.listarEnvios().subscribe({
      next: data => {
        this.envios = data;
        this.loadingEnvios = false;
      },
      error: _ => {
        this.loadingEnvios = false;
        alert('No se pudieron cargar los datos de envío.');
      }
    });
  }

  guardarCliente(): void {
    if (this.creandoCliente) {
      return;
    }

    this.mensajeCliente = null;
    const payload: NuevoCliente = {
      ...this.nuevoCliente,
      name: this.nuevoCliente.name.trim(),
      email: this.nuevoCliente.email.trim(),
      tax_id: this.nuevoCliente.tax_id.trim(),
      fiscal_address: this.nuevoCliente.fiscal_address.trim()
    };

    if (!payload.name || !payload.email || !payload.tax_id || !payload.fiscal_address) {
      alert('Completá el nombre, email, CUIT y la dirección fiscal para registrar al cliente.');
      return;
    }

    this.creandoCliente = true;
    this.api.crearCliente(payload).subscribe({
      next: client => {
        this.creandoCliente = false;
        this.nuevoCliente = this.defaultNuevoCliente();
        this.clientes = [...this.clientes, client].sort((a, b) => a.name.localeCompare(b.name));
        this.mensajeCliente = 'Cliente guardado correctamente. Ya podés seleccionarlo al emitir una factura.';
      },
      error: _ => {
        this.creandoCliente = false;
        alert('No fue posible guardar el cliente. Revisá los datos ingresados.');
      }
    });
  }

  private defaultNuevoCliente(): NuevoCliente {
    return {
      name: '',
      email: '',
      tax_id: '',
      fiscal_address: '',
      tax_condition: 5
    };
  }
}
