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

const routes: Routes = [
  { path: "", redirectTo: "cpe", pathMatch: "full" },
  { path: "cpe", component: CpeConsultaComponent },
  { path: "facturar", component: FacturarComponent },
  { path: "facturas", component: FacturasListaComponent },
  { path: "resumen", component: ResumenComponent },
];

@NgModule({
  declarations: [AppComponent, CpeConsultaComponent, FacturarComponent, FacturasListaComponent, ResumenComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule, RouterModule.forRoot(routes)],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
