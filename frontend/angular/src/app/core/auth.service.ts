import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, of, switchMap, tap, throwError } from 'rxjs';
import { ApiService, AuthTokens, AuthUser, LoginPayload, RegisterPayload } from './api.service';

const TOKEN_STORAGE_KEY = 'auth_tokens';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private userSubject = new BehaviorSubject<AuthUser | null>(null);
  private tokens: AuthTokens | null = null;

  readonly user$ = this.userSubject.asObservable();

  constructor(private api: ApiService) {
    this.restoreSession();
  }

  private restoreSession(): void {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!stored) {
      return;
    }

    try {
      const parsed: AuthTokens = JSON.parse(stored);
      if (parsed.access && parsed.refresh) {
        this.tokens = parsed;
        this.fetchProfile().subscribe({
          next: () => {},
          error: () => this.logout(),
        });
      }
    } catch (_err) {
      this.logout();
    }
  }

  get currentUser(): AuthUser | null {
    return this.userSubject.value;
  }

  getAccessToken(): string | null {
    return this.tokens?.access ?? null;
  }

  getRefreshToken(): string | null {
    return this.tokens?.refresh ?? null;
  }

  login(payload: LoginPayload): Observable<AuthUser> {
    return this.api.login(payload).pipe(
      switchMap((tokens) => this.persistTokens(tokens)),
      switchMap(() => this.fetchProfile())
    );
  }

  register(payload: RegisterPayload): Observable<AuthUser> {
    return this.api.register(payload).pipe(
      switchMap(() => this.login({ email: payload.email, password: payload.password }))
    );
  }

  refreshAccessToken(): Observable<AuthTokens> {
    const refresh = this.getRefreshToken();
    if (!refresh) {
      return throwError(() => new Error('Missing refresh token'));
    }

    return this.api.refreshToken(refresh).pipe(
      switchMap((tokens) => this.persistTokens(tokens)),
      catchError((error) => {
        this.logout();
        return throwError(() => error);
      })
    );
  }

  logout(): void {
    this.tokens = null;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    this.userSubject.next(null);
  }

  isAuthenticated(): boolean {
    return !!this.userSubject.value || !!this.tokens;
  }

  loadUserProfile(): Observable<AuthUser | null> {
    if (this.userSubject.value) {
      return of(this.userSubject.value);
    }
    if (!this.tokens) {
      return of(null);
    }
    return this.fetchProfile().pipe(
      catchError(() => {
        this.logout();
        return of(null);
      })
    );
  }

  private fetchProfile(): Observable<AuthUser> {
    return this.api.obtenerPerfil().pipe(
      tap((user) => this.userSubject.next(user))
    );
  }

  private persistTokens(tokens: AuthTokens): Observable<AuthTokens> {
    this.tokens = tokens;
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
    return of(tokens);
  }
}
