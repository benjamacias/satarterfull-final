import { Component, OnInit } from '@angular/core';
import { ApiService } from '../core/api.service';

@Component({
  selector:'app-facturas-lista',
  standalone: false,
  templateUrl:'./facturas-lista.component.html'
})
export class FacturasListaComponent implements OnInit {
  items:any[]=[]; loading=true;
  constructor(private api: ApiService) {}
  ngOnInit(){ this.api.listarFacturas().subscribe(r=>{this.items=r; this.loading=false;}); }
  enviar(id:number){ this.api.enviarFactura(id).subscribe(_=>alert('Enviado!')); }
}
