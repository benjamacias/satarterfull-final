import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { AppComponent } from './app.component';
import { CpeConsultaComponent } from './cpe-consulta/cpe-consulta.component';
import { FacturarComponent } from './facturar/facturar.component';
import { FacturasListaComponent } from './facturas-lista/facturas-lista.component';
import { ResumenComponent } from './resumen/resumen.component';
import { FacturaCpeComponent } from './factura-cpe/factura-cpe.component';
import { ProductosComponent } from './productos/productos.component';

const routes: Routes = [
  { path: "", redirectTo: "cpe", pathMatch: "full" },
  { path: "cpe", component: CpeConsultaComponent },
  { path: "facturar", component: FacturarComponent },
  { path: "facturar/cpe", component: FacturaCpeComponent },
  { path: "facturas", component: FacturasListaComponent },
  { path: "resumen", component: ResumenComponent },
  { path: "productos", component: ProductosComponent },
];

@NgModule({
  declarations: [AppComponent, CpeConsultaComponent, FacturarComponent, FacturasListaComponent, ResumenComponent, FacturaCpeComponent, ProductosComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule, RouterModule.forRoot(routes)],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
