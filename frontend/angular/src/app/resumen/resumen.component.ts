import { Component, OnInit } from '@angular/core';
import { ApiService, Client, EnvioResumen, NuevoCliente, NuevoProveedor, Producto, Provider } from '../core/api.service';

@Component({
  selector: 'app-resumen',
  standalone: false,
  templateUrl: './resumen.component.html'
})
export class ResumenComponent implements OnInit {
  clientes: Client[] = [];
  proveedores: Provider[] = [];
  productos: Producto[] = [];
  envios: EnvioResumen[] = [];
  loadingClientes = false;
  loadingProveedores = false;
  loadingProductos = false;
  loadingEnvios = false;
  creandoCliente = false;
  creandoProveedor = false;
  mensajeCliente: string | null = null;
  mensajeProveedor: string | null = null;
  nuevoCliente: NuevoCliente = this.defaultNuevoCliente();
  nuevoProveedor: NuevoProveedor = this.defaultNuevoProveedor();
  edicionProductos: Record<number, number> = {};
  actualizandoProducto: Record<number, boolean> = {};
  taxConditionOptions = [
    { value: 5, label: 'Consumidor Final' },
    { value: 4, label: 'Responsable Inscripto' },
    { value: 6, label: 'Monotributo' }
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.obtenerClientes();
    this.obtenerProveedores();
    this.obtenerProductos();
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

  private obtenerProveedores(): void {
    this.loadingProveedores = true;
    this.api.listarProveedores().subscribe({
      next: data => {
        this.proveedores = [...data].sort((a, b) => a.name.localeCompare(b.name));
        this.loadingProveedores = false;
      },
      error: _ => {
        this.loadingProveedores = false;
        alert('No se pudieron cargar los proveedores.');
      }
    });
  }

  private obtenerProductos(): void {
    this.loadingProductos = true;
    this.api.listarProductos().subscribe({
      next: data => {
        const normalizados = data.map(prod => ({
          ...prod,
          default_tariff: typeof prod.default_tariff === 'string' ? parseFloat(prod.default_tariff) : prod.default_tariff
        }));
        this.productos = normalizados;
        this.loadingProductos = false;
        this.edicionProductos = normalizados.reduce((acc, prod) => {
          acc[prod.id] = prod.default_tariff ?? 0;
          return acc;
        }, {} as Record<number, number>);
      },
      error: _ => {
        this.loadingProductos = false;
        alert('No se pudieron cargar las tarifas por producto.');
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

  guardarProveedor(): void {
    if (this.creandoProveedor) {
      return;
    }

    this.mensajeProveedor = null;
    const payload: NuevoProveedor = {
      ...this.nuevoProveedor,
      name: this.nuevoProveedor.name.trim(),
      email: this.nuevoProveedor.email.trim(),
      tax_id: this.nuevoProveedor.tax_id.trim(),
      fiscal_address: this.nuevoProveedor.fiscal_address.trim()
    };

    if (!payload.name || !payload.tax_id) {
      alert('Completá al menos el nombre y el CUIT del proveedor.');
      return;
    }

    this.creandoProveedor = true;
    this.api.crearProveedor(payload).subscribe({
      next: provider => {
        this.creandoProveedor = false;
        this.nuevoProveedor = this.defaultNuevoProveedor();
        this.proveedores = [...this.proveedores, provider].sort((a, b) => a.name.localeCompare(b.name));
        this.mensajeProveedor = 'Proveedor guardado correctamente.';
      },
      error: _ => {
        this.creandoProveedor = false;
        alert('No fue posible guardar el proveedor.');
      }
    });
  }

  actualizarTarifaProducto(producto: Producto): void {
    const valor = this.edicionProductos[producto.id];
    if (valor === undefined || valor === null || isNaN(valor)) {
      return;
    }
    this.actualizandoProducto[producto.id] = true;
    this.api.actualizarProducto(producto.id, { default_tariff: valor }).subscribe({
      next: actualizado => {
        this.actualizandoProducto[producto.id] = false;
        const normalizado = {
          ...actualizado,
          default_tariff:
            typeof actualizado.default_tariff === 'string'
              ? parseFloat(actualizado.default_tariff)
              : actualizado.default_tariff
        };
        this.productos = this.productos.map(p => (p.id === normalizado.id ? normalizado : p));
        this.edicionProductos[normalizado.id] = normalizado.default_tariff ?? 0;
      },
      error: _ => {
        this.actualizandoProducto[producto.id] = false;
        alert('No se pudo actualizar la tarifa del producto.');
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

  private defaultNuevoProveedor(): NuevoProveedor {
    return {
      name: '',
      email: '',
      tax_id: '',
      fiscal_address: ''
    };
  }
}
