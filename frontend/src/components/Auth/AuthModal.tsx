import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AuthCard } from './AuthCard.tsx';

interface AuthModalProps {
  isOpen: boolean;
  mode: 'signup' | 'login' | 'closed';
  onClose: () => void;
  onSwitchMode: (mode: 'signup' | 'login') => void;
  clientX: number;
  clientY: number;
  isIdle: boolean;
  onSuccessNavigate?: () => void;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  mode,
  onClose,
  onSwitchMode,
  clientX,
  clientY,
  isIdle,
  onSuccessNavigate,
  onHoverStart,
  onHoverEnd,
}) => {
  const modalRef = useRef<HTMLDivElement | null>(null);

  const isReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Handle Escape key and focus trap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }

      if (e.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const focusable = Array.from(focusableElements).filter(
          (el) => !el.hasAttribute('disabled') && el.offsetParent !== null
        );

        if (focusable.length === 0) return;

        const firstElement = focusable[0];
        const lastElement = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    // Auto-focus first input on open after animation start
    const timer = setTimeout(() => {
      if (modalRef.current) {
        const firstInput = modalRef.current.querySelector<HTMLInputElement>('input');
        firstInput?.focus();
      }
    }, 150);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      clearTimeout(timer);
    };
  }, [isOpen, onClose]);

  const activeMode = mode === 'login' ? 'login' : 'signup';

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="auth-modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 select-none"
          style={{
            background: 'rgba(236, 236, 238, 0.94)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-dialog-title"
          aria-describedby="auth-dialog-subtitle"
        >
          {/* Clickable Backdrop Area for Closing */}
          <div
            onClick={onClose}
            className="absolute inset-0 z-10 cursor-pointer"
            aria-hidden="true"
          />

          {/* Centered Modal Card Container */}
          <div
            ref={modalRef}
            className="relative z-20 w-full flex justify-center items-center pointer-events-auto"
          >
            <motion.div
              initial={
                isReducedMotion
                  ? { opacity: 0 }
                  : { opacity: 0, y: 20, scale: 0.97 }
              }
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={
                isReducedMotion
                  ? { opacity: 0 }
                  : { opacity: 0, y: 16, scale: 0.97 }
              }
              transition={{
                duration: 0.7,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="flex justify-center"
            >
              <AuthCard
                initialMode={activeMode}
                onClose={onClose}
                onSwitchMode={onSwitchMode}
                onSuccessNavigate={onSuccessNavigate}
                clientX={clientX}
                clientY={clientY}
                isIdle={isIdle}
                onHoverStart={onHoverStart}
                onHoverEnd={onHoverEnd}
              />
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
