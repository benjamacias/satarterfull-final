import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE = 'http://localhost:8000/api';

export interface Client {
  id: number;
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
  tax_condition: number;
  tax_condition_display: string;
}

export interface EnvioFactura {
  client_id: number | null;
  amount: number;
  pto_vta: number;
  cbte_tipo: number;
  doc_tipo: number;
  doc_nro: string;
  condicion_iva_receptor_id?: number | null;
}

export interface NuevoCliente {
  name: string;
  email: string;
  tax_id: string;
  fiscal_address: string;
  tax_condition: number;
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
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  consultarCPE(nro_ctg: string): Observable<any> {
    return this.http.post(`${API_BASE}/cpe/consultar/`, { nro_ctg });
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

  listarEnvios(): Observable<EnvioResumen[]> {
    return this.http.get<EnvioResumen[]>(`${API_BASE}/envios/`);
  }
}
