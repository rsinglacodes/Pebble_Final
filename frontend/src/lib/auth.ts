   import { ApiError, USER_KEY, clearStoredAuth, getToken, request, setToken } from './api.ts';

   export interface AuthUser { id: string; name: string; email: string; avatar?: string }
   export interface AuthResponse { user: AuthUser; token?: string }
   export interface SignUpParams { name: string; email: string; password: string }
   export interface LogInParams { email: string; password: string }

   interface ApiUser { id: string; name: string; email: string }
   const toUser = (u: ApiUser): AuthUser => ({ id: u.id, name: u.name, email: u.email });
   const saveUser = (u: AuthUser) => { try { localStorage.setItem(USER_KEY, JSON.stringify(u)); } catch {} };

   export function getSavedSession(): AuthUser | null {
     try {
       if (!getToken()) return null;
       const raw = localStorage.getItem(USER_KEY);
       return raw ? JSON.parse(raw) : null;
     } catch { return null; }
   }
   export const clearSession = clearStoredAuth;

   export async function fetchCurrentUser(): Promise<AuthUser> {
     const user = toUser(await request<ApiUser>('/users/me'));
     saveUser(user);
     return user;
   }

   export async function signUp({ name, email, password }: SignUpParams): Promise<AuthResponse> {
     const e = email.trim().toLowerCase();
     const created = await request<ApiUser>('/auth/register', {
       method: 'POST', auth: false, body: { name: name.trim(), email: e, password },
     });
     try {
       const { access_token } = await request<{ access_token: string }>('/auth/login', {
         method: 'POST', auth: false, body: { email: e, password },
       });
       setToken(access_token);
       const user = toUser(created);
       saveUser(user);
       return { user, token: access_token };
     } catch (err) {
       throw new ApiError('Your account was created, but automatic log in failed. Please switch to Log in.',
         err instanceof ApiError ? err.status : 0);
     }
   }

   export async function logIn({ email, password }: LogInParams): Promise<AuthResponse> {
     const { access_token } = await request<{ access_token: string }>('/auth/login', {
       method: 'POST', auth: false, body: { email: email.trim().toLowerCase(), password },
     });
     setToken(access_token);
     try { return { user: await fetchCurrentUser(), token: access_token }; }
     catch (err) { clearStoredAuth(); throw err; }
   }

   export async function signInWithGoogle(): Promise<AuthResponse> {
     throw new ApiError('Google sign-in is not available yet. Please use your email and password.', 501);
   }