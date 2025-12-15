import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-register',
  standalone: false,
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  email = '';
  password = '';
  phone = '';
  firstName = '';
  lastName = '';
  loading = false;
  error: string | null = null;

  constructor(private authService: AuthService, private router: Router) {}

  onSubmit(): void {
    if (!this.email || !this.password || !this.phone) {
      this.error = 'Completa correo, contraseña y teléfono';
      return;
    }
    this.error = null;
    this.loading = true;
    this.authService
      .register({
        email: this.email,
        password: this.password,
        phone_number: this.phone,
        first_name: this.firstName || undefined,
        last_name: this.lastName || undefined,
      })
      .subscribe({
        next: () => {
          this.loading = false;
          this.router.navigate(['/cpe']);
        },
        error: () => {
          this.loading = false;
          this.error = 'No pudimos crear tu cuenta. Inténtalo nuevamente.';
        },
      });
  }
}
