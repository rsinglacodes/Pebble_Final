   const TOKEN_KEY = 'pebble_token';
   export const USER_KEY = 'pebble_user';
   export const UNAUTHORIZED_EVENT = 'pebble:unauthorized';
   export const API_BASE =
     ((import.meta.env.VITE_API_URL as string | undefined) ?? '').trim().replace(/\/+$/, '') || '/api';

   export class ApiError extends Error {
     status: number;
     constructor(message: string, status: number) {
       super(message); this.name = 'ApiError'; this.status = status;
     }
   }

   export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
   export const setToken = (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch {} };
   export const clearStoredAuth = () => {
     try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); } catch {}
   };

   function friendlyMessage(status: number, data: any): string {
     const msg = typeof data?.message === 'string' ? data.message
               : typeof data?.detail === 'string' ? data.detail : '';
     if (status >= 500 && data === null)
       return "Can't reach the pebble server. Check that the backend is running.";
     switch (status) {
       case 401: return /invalid email or password/i.test(msg)
         ? 'Incorrect email or password.' : 'Your session has expired. Please log in again.';
       case 409: return 'An account with this email already exists. Try logging in instead.';
       case 422: return 'Please check the details you entered and try again.';
       case 429: return 'Too many attempts. Please wait a minute and try again.';
       default: return status >= 500
         ? 'The server ran into a problem. Please try again in a moment.'
         : msg || 'Something went wrong. Please try again.';
     }
   }

   export async function request<T>(
     path: string,
     opts: { method?: 'GET'|'POST'|'PATCH'|'DELETE'; body?: unknown; auth?: boolean; signal?: AbortSignal } = {}
   ): Promise<T> {
     const { method = 'GET', body, auth = true, signal } = opts;
     const headers: Record<string, string> = { Accept: 'application/json' };
     if (body !== undefined) headers['Content-Type'] = 'application/json';
     if (auth) { const t = getToken(); if (t) headers.Authorization = `Bearer ${t}`; }

     let res: Response;
     try {
       res = await fetch(`${API_BASE}${path}`, {
         method, headers, signal,
         body: body !== undefined ? JSON.stringify(body) : undefined,
       });
     } catch (err) {
       if ((err as any)?.name === 'AbortError') throw err;
       throw new ApiError("Can't reach the pebble server. Check that the backend is running.", 0);
     }

     let data: any = null;
     const text = await res.text();
     if (text) { try { data = JSON.parse(text); } catch { data = null; } }

     if (!res.ok) {
       if (res.status === 401 && auth) {
         clearStoredAuth();
         window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
       }
       throw new ApiError(friendlyMessage(res.status, data), res.status);
     }
     return data as T;
   }