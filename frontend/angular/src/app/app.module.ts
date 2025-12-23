import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RouterModule, Routes } from '@angular/router';
import { AppComponent } from './app.component';
import { CpeConsultaComponent } from './cpe-consulta/cpe-consulta.component';
import { FacturarComponent } from './facturar/facturar.component';
import { FacturasListaComponent } from './facturas-lista/facturas-lista.component';
import { ResumenComponent } from './resumen/resumen.component';
import { FacturaCpeComponent } from './factura-cpe/factura-cpe.component';
import { ProductosComponent } from './productos/productos.component';
import { VehiculosDashboardComponent } from './vehiculos-dashboard/vehiculos-dashboard.component';
import { LoginComponent } from './auth/login/login.component';
import { RegisterComponent } from './auth/register/register.component';
import { AuthGuard } from './core/auth.guard';
import { AdminGuard } from './core/admin.guard';
import { AuthInterceptor } from './core/auth.interceptor';

const routes: Routes = [
  { path: '', redirectTo: 'cpe', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'cpe', component: CpeConsultaComponent, canActivate: [AuthGuard] },
  { path: 'facturar', component: FacturarComponent, canActivate: [AuthGuard] },
  { path: 'facturar/cpe', component: FacturaCpeComponent, canActivate: [AuthGuard] },
  { path: 'facturas', component: FacturasListaComponent, canActivate: [AuthGuard] },
  { path: 'resumen', component: ResumenComponent, canActivate: [AuthGuard] },
  { path: 'productos', component: ProductosComponent, canActivate: [AuthGuard] },
  { path: 'vehiculos-dashboard', component: VehiculosDashboardComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: 'cpe' },
];

@NgModule({
  declarations: [AppComponent, CpeConsultaComponent, FacturarComponent, FacturasListaComponent, ResumenComponent, FacturaCpeComponent, ProductosComponent, VehiculosDashboardComponent, LoginComponent, RegisterComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule, RouterModule.forRoot(routes)],
  providers: [
    AuthGuard,
    AdminGuard,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
