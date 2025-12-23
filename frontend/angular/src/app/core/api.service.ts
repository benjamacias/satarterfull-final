import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE = '/api';

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthUser {
  id: number;
  email: string;
  phone_number?: string;
  first_name?: string;
  last_name?: string;
  is_staff?: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  phone_number: string;
  first_name?: string;
  last_name?: string;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
  tax_condition: number;
  tax_condition_display: string;
}

export interface Provider {
  id: number;
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
}

export interface ComprobanteAsociado {
  tipo: number;
  pto_vta: number;
  nro: number;
  cuit?: string;
  cbte_fch?: string;
}

export interface PeriodoAsociado {
  desde: string;
  hasta: string;
}

export interface EnvioFactura {
  client_id: number | null;
  amount: number;
  pto_vta: number;
  cbte_tipo: number;
  doc_tipo: number;
  doc_nro: string;
  condicion_iva_receptor_id?: number | null;
  cbtes_asoc?: ComprobanteAsociado | ComprobanteAsociado[] | null;
  periodo_asoc?: PeriodoAsociado | null;
  concepto?: number | null;
  issue_date?: string | null;
  service_start?: string | null;
  service_end?: string | null;
  payment_due?: string | null;
}

export interface NuevoCliente {
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
  tax_condition: number;
}

export interface NuevoProveedor {
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
}

export interface EnvioResumen {
  id: number;
  nro_ctg: string;
  tipo_carta_porte: string | null;
  estado: string | null;
  fecha_emision: string | null;
  fecha_vencimiento: string | null;
  sucursal: number | null;
  nro_orden: number | null;
  vehicle_domain: string | null;
}

export interface Producto {
  id: number;
  name: string;
  afip_code: string | null;
  default_tariff: number;
}

export interface NuevoProducto {
  name: string;
  afip_code: string | null;
  default_tariff: number;
}

export interface CpeFacturaDetalle {
  id: number;
  nro_ctg: string;
  fecha_emision: string | null;
  nro_orden: number | null;
  product_description: string;
  procedencia: string;
  destino: string;
  peso_bruto_descarga: number | null;
  net_weight: number | null;
  tariff: number | null;
  total_amount: number | null;
  client_id: number | null;
  client_name: string | null;
  provider_id: number | null;
  provider_name: string | null;
  product_id: number | null;
  product_name: string | null;
  product_code: string | null;
  vehicle_domain: string | null;
  vehicle?: number | null;
}

export interface DominioEstadistica {
  dominio: string;
  movimientos: number;
  total_ctg: number;
  facturacion: number;
}

export interface EstadisticasDominiosResponse {
  mayores_movimientos: DominioEstadistica[];
  mayor_facturacion: DominioEstadistica[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  consultarCPE(nro_ctg: string, peso_bruto_descarga?: number | null): Observable<any> {
    const payload: { nro_ctg: string; peso_bruto_descarga?: number | null } = { nro_ctg };
    if (peso_bruto_descarga !== undefined) {
      payload.peso_bruto_descarga = peso_bruto_descarga;
    }
    return this.http.post(`${API_BASE}/cpe/consultar/`, payload);
  }

  emitirFactura(payload: EnvioFactura): Observable<any> {
    return this.http.post(`${API_BASE}/facturas/emitir/`, payload);
  }

  listarFacturas(): Observable<any[]> {
    return this.http.get<any[]>(`${API_BASE}/facturas/`);
  }

  enviarFactura(id: number): Observable<any> {
    return this.http.post(`${API_BASE}/${id}/facturas/enviar/`, {});
  }

  listarClientes(): Observable<Client[]> {
    return this.http.get<Client[]>(`${API_BASE}/clientes/`);
  }

  crearCliente(payload: NuevoCliente): Observable<Client> {
    return this.http.post<Client>(`${API_BASE}/clientes/`, payload);
  }

  actualizarCliente(clienteId: number, payload: NuevoCliente): Observable<Client> {
    return this.http.put<Client>(`${API_BASE}/clientes/${clienteId}/`, payload);
  }

  listarProveedores(): Observable<Provider[]> {
    return this.http.get<Provider[]>(`${API_BASE}/proveedores/`);
  }

  crearProveedor(payload: NuevoProveedor): Observable<Provider> {
    return this.http.post<Provider>(`${API_BASE}/proveedores/`, payload);
  }

  listarEnvios(): Observable<EnvioResumen[]> {
    return this.http.get<EnvioResumen[]>(`${API_BASE}/envios/`);
  }

  listarProductos(): Observable<Producto[]> {
    return this.http.get<Producto[]>(`${API_BASE}/productos/`);
  }

  crearProducto(payload: NuevoProducto): Observable<Producto> {
    return this.http.post<Producto>(`${API_BASE}/productos/`, payload);
  }

  editarProductoCompleto(productoId: number, payload: NuevoProducto): Observable<Producto> {
    return this.http.put<Producto>(`${API_BASE}/productos/${productoId}/`, payload);
  }

  actualizarProducto(productoId: number, payload: Partial<Producto>): Observable<Producto> {
    return this.http.patch<Producto>(`${API_BASE}/productos/${productoId}/`, payload);
  }

  listarCpePorCliente(clienteId: number): Observable<CpeFacturaDetalle[]> {
    return this.http.get<CpeFacturaDetalle[]>(`${API_BASE}/clientes/${clienteId}/cpe/`);
  }

  actualizarTarifaCpe(cpeId: number, tarifa: number): Observable<CpeFacturaDetalle> {
    return this.http.patch<CpeFacturaDetalle>(`${API_BASE}/cpe/${cpeId}/tarifa/`, { tariff: tarifa });
  }

  descargarPdfCpe(cpeId: number): Observable<Blob> {
    return this.http.get(`${API_BASE}/cpe/${cpeId}/pdf/`, { responseType: 'blob' });
  }

  obtenerEstadisticasDominios(): Observable<EstadisticasDominiosResponse> {
    return this.http.get<EstadisticasDominiosResponse>(`${API_BASE}/estadisticas/dominios/`);
  }

  login(payload: LoginPayload): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${API_BASE}/auth/login/`, payload);
  }

  register(payload: RegisterPayload): Observable<AuthUser> {
    return this.http.post<AuthUser>(`${API_BASE}/auth/register/`, payload);
  }

  refreshToken(refresh: string): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${API_BASE}/auth/refresh/`, { refresh });
  }

  obtenerPerfil(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${API_BASE}/auth/profile/`);
  }
}
