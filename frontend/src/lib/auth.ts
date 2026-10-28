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

   function loadGoogleScript(): Promise<void> {
     return new Promise((resolve, reject) => {
       if (typeof window !== 'undefined' && (window as any).google?.accounts?.id) {
         resolve();
         return;
       }
       const existing = document.getElementById('google-gis-script');
       if (existing) {
         existing.addEventListener('load', () => resolve());
         existing.addEventListener('error', () => reject(new ApiError('Failed to load Google Sign-In SDK', 500)));
         return;
       }
       const script = document.createElement('script');
       script.id = 'google-gis-script';
       script.src = 'https://accounts.google.com/gsi/client';
       script.async = true;
       script.defer = true;
       script.onload = () => resolve();
       script.onerror = () => reject(new ApiError('Failed to load Google Sign-In SDK', 500));
       document.head.appendChild(script);
     });
   }

   function getGoogleCredential(): Promise<string> {
     return new Promise(async (resolve, reject) => {
       try {
         await loadGoogleScript();
       } catch (e) {
         return reject(e);
       }

       const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
       if (!clientId) {
         return reject(new ApiError('VITE_GOOGLE_CLIENT_ID is not configured in environment variables.', 500));
       }

       const google = (window as any).google;
       if (!google?.accounts?.id) {
         return reject(new ApiError('Google Identity Services not available.', 500));
       }

       let settled = false;

       google.accounts.id.initialize({
         client_id: clientId,
         callback: (res: { credential?: string }) => {
           if (settled) return;
           settled = true;
           if (res.credential) {
             resolve(res.credential);
           } else {
             reject(new ApiError('No credential received from Google.', 400));
           }
         },
         auto_select: false,
         cancel_on_tap_outside: true,
       });

       google.accounts.id.prompt((notification: any) => {
         if (settled) return;
         if (notification.isNotDisplayed()) {
           settled = true;
           const reason = notification.getNotDisplayedReason() || 'unknown';
           reject(new ApiError(`Google Sign-In prompt could not be displayed (${reason}).`, 400));
         } else if (notification.isSkippedMoment()) {
           settled = true;
           const reason = notification.getSkippedReason() || 'unknown';
           reject(new ApiError(`Google Sign-In prompt skipped (${reason}).`, 400));
         } else if (notification.isDismissedMoment()) {
           settled = true;
           const reason = notification.getDismissedReason() || 'dismissed';
           reject(new ApiError(`Google Sign-In cancelled (${reason}).`, 400));
         }
       });
     });
   }

   export async function signInWithGoogle(): Promise<AuthResponse> {
     const credential = await getGoogleCredential();
     const { access_token } = await request<{ access_token: string }>('/auth/google', {
       method: 'POST',
       auth: false,
       body: { credential },
     });
     setToken(access_token);
     try {
       return { user: await fetchCurrentUser(), token: access_token };
     } catch (err) {
       clearStoredAuth();
       throw err;
     }
   }