import { Component, OnInit } from '@angular/core';
import { ApiService, Producto } from '../core/api.service';

interface ProductoForm {
  id: number | null;
  name: string;
  afip_code: string;
  default_tariff: number | null;
}

@Component({
  selector: 'app-productos',
  standalone: false,
  templateUrl: './productos.component.html',
  styleUrls: ['./productos.component.scss']
})
export class ProductosComponent implements OnInit {
  productos: Producto[] = [];
  loading = false;
  error: string | null = null;
  success: string | null = null;
  form: ProductoForm = this.initialForm();

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.cargarProductos();
  }

  cargarProductos(): void {
    this.loading = true;
    this.api.listarProductos().subscribe({
      next: (items) => {
        this.productos = items;
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudieron cargar los productos. Intenta nuevamente.';
        this.loading = false;
      }
    });
  }

  prepararCreacion(): void {
    this.resetFeedback();
    this.form = this.initialForm();
  }

  editar(producto: Producto): void {
    this.resetFeedback();
    this.form = {
      id: producto.id,
      name: producto.name,
      afip_code: producto.afip_code ?? '',
      default_tariff: producto.default_tariff
    };
  }

  guardar(): void {
    this.resetFeedback();
    if (!this.validarFormulario()) {
      this.error = 'Por favor completa los campos requeridos antes de continuar.';
      return;
    }

    const payload = {
      name: this.form.name.trim(),
      afip_code: this.form.afip_code.trim() || null,
      default_tariff: Number(this.form.default_tariff)
    };

    if (this.form.id) {
      this.api.editarProductoCompleto(this.form.id, payload).subscribe({
        next: (productoActualizado) => {
          this.productos = this.productos.map((item) =>
            item.id === productoActualizado.id ? productoActualizado : item
          );
          this.success = 'Producto actualizado correctamente.';
          this.form = this.initialForm();
        },
        error: () => {
          this.error = 'No se pudo actualizar el producto. Intenta nuevamente.';
        }
      });
    } else {
      this.api.crearProducto(payload).subscribe({
        next: (nuevoProducto) => {
          this.productos = [nuevoProducto, ...this.productos];
          this.success = 'Producto creado correctamente.';
          this.form = this.initialForm();
        },
        error: () => {
          this.error = 'No se pudo crear el producto. Intenta nuevamente.';
        }
      });
    }
  }

  cancelarEdicion(): void {
    this.form = this.initialForm();
    this.resetFeedback();
  }

  private validarFormulario(): boolean {
    return !!this.form.name.trim() && this.form.default_tariff !== null && this.form.default_tariff >= 0;
  }

  private resetFeedback(): void {
    this.error = null;
    this.success = null;
  }

  private initialForm(): ProductoForm {
    return {
      id: null,
      name: '',
      afip_code: '',
      default_tariff: null
    };
  }
}
