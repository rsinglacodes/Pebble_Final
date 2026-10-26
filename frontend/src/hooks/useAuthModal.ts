import { useState, useEffect, useCallback, useRef } from 'react';

export type AuthMode = 'closed' | 'signup' | 'login';

export interface UseAuthModalReturn {
  mode: AuthMode;
  isOpen: boolean;
  openSignUp: () => void;
  openLogIn: () => void;
  switchMode: (newMode: 'signup' | 'login') => void;
  close: () => void;
  triggerRef: React.MutableRefObject<HTMLElement | null>;
}

export function useAuthModal(): UseAuthModalReturn {
  const [mode, setMode] = useState<AuthMode>(() => {
    if (typeof window === 'undefined') return 'closed';
    const hash = window.location.hash.toLowerCase();
    if (hash === '#signup') return 'signup';
    if (hash === '#login') return 'login';
    return 'closed';
  });

  const triggerRef = useRef<HTMLElement | null>(null);
  const scrollPositionRef = useRef<number>(0);

  // Synchronize state with window hash (supporting direct loads and browser Back/Forward)
  const syncFromHash = useCallback(() => {
    const hash = window.location.hash.toLowerCase();
    if (hash === '#signup') {
      setMode('signup');
    } else if (hash === '#login') {
      setMode('login');
    } else {
      setMode('closed');
    }
  }, []);

  useEffect(() => {
    window.addEventListener('hashchange', syncFromHash);
    window.addEventListener('popstate', syncFromHash);
    return () => {
      window.removeEventListener('hashchange', syncFromHash);
      window.removeEventListener('popstate', syncFromHash);
    };
  }, [syncFromHash]);

  const isOpen = mode !== 'closed';

  // Handle scroll lock and restoration on html element
  useEffect(() => {
    if (isOpen) {
      scrollPositionRef.current = window.scrollY || document.documentElement.scrollTop;
      const htmlEl = document.documentElement;
      const originalOverflow = htmlEl.style.overflow;
      htmlEl.style.overflow = 'hidden';

      return () => {
        htmlEl.style.overflow = '';
        if (originalOverflow && originalOverflow !== 'hidden') {
          htmlEl.style.overflow = originalOverflow;
        }

        window.scrollTo({
          top: scrollPositionRef.current,
          behavior: 'instant' as ScrollBehavior,
        });

        if (triggerRef.current) {
          triggerRef.current.focus();
          triggerRef.current = null;
        }
      };
    }
  }, [isOpen]);

  const openSignUp = useCallback(() => {
    if (typeof document !== 'undefined' && document.activeElement instanceof HTMLElement) {
      triggerRef.current = document.activeElement;
    }
    setMode('signup');
    if (window.location.hash !== '#signup') {
      history.pushState(null, '', '#signup');
    }
  }, []);

  const openLogIn = useCallback(() => {
    if (typeof document !== 'undefined' && document.activeElement instanceof HTMLElement) {
      triggerRef.current = document.activeElement;
    }
    setMode('login');
    if (window.location.hash !== '#login') {
      history.pushState(null, '', '#login');
    }
  }, []);

  const switchMode = useCallback((newMode: 'signup' | 'login') => {
    setMode(newMode);
    const targetHash = `#${newMode}`;
    if (window.location.hash !== targetHash) {
      history.replaceState(null, '', targetHash);
    }
  }, []);

  const close = useCallback(() => {
    setMode('closed');
    // Remove hash without jumping scroll position
    if (window.location.hash) {
      const cleanUrl = window.location.pathname + window.location.search;
      history.pushState(null, '', cleanUrl);
    }
  }, []);

  return {
    mode,
    isOpen,
    openSignUp,
    openLogIn,
    switchMode,
    close,
    triggerRef,
  };
}
