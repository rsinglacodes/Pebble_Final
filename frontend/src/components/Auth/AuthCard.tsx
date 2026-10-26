import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';
import { SignUpForm } from './SignUpForm.tsx';
import { LogInForm } from './LogInForm.tsx';
import { SuccessView } from './SuccessView.tsx';
import { AuthShowcase } from './AuthShowcase.tsx';
import { authContent } from '../../content.ts';
import { signInWithGoogle } from '../../lib/auth.ts';

interface AuthCardProps {
  initialMode: 'signup' | 'login';
  onClose: () => void;
  onSwitchMode: (mode: 'signup' | 'login') => void;
  onSuccessNavigate?: () => void;
  clientX: number;
  clientY: number;
  isIdle: boolean;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const AuthCard: React.FC<AuthCardProps> = ({
  initialMode,
  onClose,
  onSwitchMode,
  onSuccessNavigate,
  clientX,
  clientY,
  isIdle,
  onHoverStart,
  onHoverEnd,
}) => {
  const [activeTab, setActiveTab] = useState<'signup' | 'login'>(initialMode);
  const [direction, setDirection] = useState<number>(0);
  const [isSuccess, setIsSuccess] = useState(false);
  const [successUser, setSuccessUser] = useState<string>('');
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);

  const isReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const handleTabChange = (tab: 'signup' | 'login') => {
    if (tab === activeTab) return;
    setDirection(tab === 'login' ? 1 : -1);
    setActiveTab(tab);
    onSwitchMode(tab);
  };

  const triggerShake = () => {
    if (!isReducedMotion) {
      setShakeKey((prev) => prev + 1);
    }
  };

  const handleAuthSuccess = (name: string) => {
    setSuccessUser(name);
    setIsSuccess(true);
  };

  const handleGoogleSignIn = async () => {
    setIsGoogleLoading(true);
    try {
      const res = await signInWithGoogle();
      handleAuthSuccess(res.user.name);
    } catch {
      triggerShake();
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const titleText =
    activeTab === 'signup'
      ? authContent.titles.signup.title
      : authContent.titles.login.title;

  const subtitleText =
    activeTab === 'signup'
      ? authContent.titles.signup.subtitle
      : authContent.titles.login.subtitle;

  return (
    <motion.div
      key={shakeKey}
      animate={
        shakeKey > 0 && !isReducedMotion
          ? { x: [-6, 6, -5, 5, -3, 3, 0] }
          : { x: 0 }
      }
      transition={{ duration: 0.3 }}
      className="relative w-[min(1040px,calc(100vw-48px))] max-[899px]:w-[min(460px,calc(100vw-32px))] h-[min(700px,calc(100vh-48px))] max-[899px]:h-auto max-[899px]:max-h-[calc(100vh-32px)] bg-[#FAFAFB] rounded-[28px] border border-black/[0.06] shadow-[0_30px_80px_rgba(17,17,17,0.12)] p-3 grid grid-cols-1 min-[900px]:grid-cols-2 gap-3 select-none overflow-hidden"
    >
      {/* Round "X" Close Button at top right */}
      <button
        type="button"
        onClick={onClose}
        onMouseEnter={() => onHoverStart?.('button')}
        onMouseLeave={onHoverEnd}
        data-cursor="button"
        aria-label="Close dialog"
        className="absolute top-4 right-4 sm:top-5 sm:right-5 w-9 h-9 rounded-full bg-white text-[#55555D] hover:text-[#111113] border border-black/[0.08] shadow-[0_2px_8px_rgba(0,0,0,0.08)] flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-[#111113]/20 z-30 cursor-pointer"
      >
        <X className="w-4 h-4 stroke-[2]" />
      </button>

      {/* LEFT PANEL: The Form */}
      <div className="relative w-full h-full flex flex-col justify-center overflow-y-auto overflow-x-hidden px-[clamp(24px,3.8vw,52px)] py-4 sm:py-6 auth-scrollbar">
        {isSuccess ? (
          <SuccessView
            userName={successUser}
            isSignUp={activeTab === 'signup'}
            onContinue={onSuccessNavigate || onClose}
            onHoverStart={onHoverStart}
            onHoverEnd={onHoverEnd}
          />
        ) : (
          <div className="w-full my-auto flex flex-col">
            {/* 1. Small Brand Row Aligned Left */}
            <div className="flex items-center gap-2.5 mb-4">
              <div
                className="relative w-7 h-6 sm:w-8 sm:h-7 rounded-[48%_52%_68%_32%_/_42%_44%_56%_58%] p-[2px] shadow-2xs"
                style={{
                  background:
                    'linear-gradient(135deg, #8B5CF6 0%, #6366F1 45%, #06B6D4 100%)',
                }}
              >
                <div className="w-full h-full bg-[#121217] rounded-[46%_54%_66%_34%_/_40%_42%_58%_60%] flex items-center justify-center gap-1.5 px-1 shadow-inner overflow-hidden relative">
                  <div className="absolute -top-1 -left-1 w-2.5 h-2.5 bg-white/25 rounded-full blur-[1px]" />
                  <span className="w-1.5 h-2.5 bg-gradient-to-b from-white to-[#C7D2FE] rounded-full" />
                  <span className="w-1.5 h-2.5 bg-gradient-to-b from-white to-[#A5F3FC] rounded-full" />
                </div>
              </div>

              <span className="text-xl font-bold tracking-tight text-[#111113]">
                {authContent.brand.name}
              </span>
            </div>

            {/* 2. Heading */}
            <div className="mb-4 text-left">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: isReducedMotion ? 0 : 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: isReducedMotion ? 0 : -4 }}
                  transition={{ duration: 0.18 }}
                >
                  <h2
                    id="auth-dialog-title"
                    className="text-[25px] sm:text-[28px] font-semibold text-[#111113] tracking-tight leading-[1.15]"
                  >
                    {titleText}
                  </h2>
                  <p
                    id="auth-dialog-subtitle"
                    className="text-[14px] sm:text-[15px] text-[#6B6B73] mt-1 font-normal leading-normal"
                  >
                    {subtitleText}
                  </p>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* 3. Segmented Tab Switch */}
            <div
              className="relative w-full h-[44px] rounded-[12px] p-1 flex items-center mb-4 bg-black/[0.05]"
              role="tablist"
              aria-label="Authentication modes"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'signup'}
                onClick={() => handleTabChange('signup')}
                onMouseEnter={() => onHoverStart?.('tab')}
                onMouseLeave={onHoverEnd}
                data-cursor="button"
                className={`relative flex-1 h-full rounded-[9px] text-[14px] sm:text-[15px] font-medium transition-colors duration-200 flex items-center justify-center z-10 cursor-pointer ${
                  activeTab === 'signup'
                    ? 'text-[#111113]'
                    : 'text-[#8A8A90] hover:text-[#55555D]'
                }`}
              >
                {activeTab === 'signup' && (
                  <motion.div
                    layoutId="activeAuthTab"
                    className="absolute inset-0 bg-white rounded-[9px] border border-black/[0.04] shadow-[0_2px_6px_rgba(0,0,0,0.05)] z-[-1]"
                    transition={
                      isReducedMotion
                        ? { duration: 0.1 }
                        : { type: 'spring', stiffness: 380, damping: 32 }
                    }
                  />
                )}
                <span>{authContent.tabs.signup}</span>
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'login'}
                onClick={() => handleTabChange('login')}
                onMouseEnter={() => onHoverStart?.('tab')}
                onMouseLeave={onHoverEnd}
                data-cursor="button"
                className={`relative flex-1 h-full rounded-[9px] text-[14px] sm:text-[15px] font-medium transition-colors duration-200 flex items-center justify-center z-10 cursor-pointer ${
                  activeTab === 'login'
                    ? 'text-[#111113]'
                    : 'text-[#8A8A90] hover:text-[#55555D]'
                }`}
              >
                {activeTab === 'login' && (
                  <motion.div
                    layoutId="activeAuthTab"
                    className="absolute inset-0 bg-white rounded-[9px] border border-black/[0.04] shadow-[0_2px_6px_rgba(0,0,0,0.05)] z-[-1]"
                    transition={
                      isReducedMotion
                        ? { duration: 0.1 }
                        : { type: 'spring', stiffness: 380, damping: 32 }
                    }
                  />
                )}
                <span>{authContent.tabs.login}</span>
              </button>
            </div>

            {/* 4. Form Fields */}
            <div className="relative w-full overflow-hidden">
              <AnimatePresence mode="wait" initial={false}>
                {activeTab === 'signup' ? (
                  <motion.div
                    key="signup-panel"
                    initial={
                      isReducedMotion
                        ? { opacity: 0 }
                        : { opacity: 0, x: direction === 1 ? -14 : 14 }
                    }
                    animate={{ opacity: 1, x: 0 }}
                    exit={
                      isReducedMotion
                        ? { opacity: 0 }
                        : { opacity: 0, x: direction === 1 ? 14 : -14 }
                    }
                    transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                    className="w-full"
                  >
                    <SignUpForm
                      onSuccess={handleAuthSuccess}
                      onSwitchToLogIn={() => handleTabChange('login')}
                      onGoogleSignIn={handleGoogleSignIn}
                      isGoogleLoading={isGoogleLoading}
                      onTriggerShake={triggerShake}
                      onHoverStart={onHoverStart}
                      onHoverEnd={onHoverEnd}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="login-panel"
                    initial={
                      isReducedMotion
                        ? { opacity: 0 }
                        : { opacity: 0, x: direction === 1 ? 14 : -14 }
                    }
                    animate={{ opacity: 1, x: 0 }}
                    exit={
                      isReducedMotion
                        ? { opacity: 0 }
                        : { opacity: 0, x: direction === 1 ? -14 : 14 }
                    }
                    transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                    className="w-full"
                  >
                    <LogInForm
                      onSuccess={handleAuthSuccess}
                      onSwitchToSignUp={() => handleTabChange('signup')}
                      onGoogleSignIn={handleGoogleSignIn}
                      isGoogleLoading={isGoogleLoading}
                      onTriggerShake={triggerShake}
                      onHoverStart={onHoverStart}
                      onHoverEnd={onHoverEnd}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT PANEL: Robot Showcase */}
      <div className="hidden min-[900px]:block relative w-full h-full overflow-hidden">
        <AuthShowcase
          clientX={clientX}
          clientY={clientY}
          isIdle={isIdle}
          isSuccess={isSuccess}
        />
      </div>

      <style>{`
        .auth-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: rgba(17, 17, 17, 0.15) transparent;
        }
        .auth-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .auth-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .auth-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(17, 17, 17, 0.15);
          border-radius: 9999px;
        }
      `}</style>
    </motion.div>
  );
};
