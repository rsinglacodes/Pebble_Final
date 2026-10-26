import React, { forwardRef, useState } from 'react';
import { Eye, EyeOff, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface PasswordFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  showStrength?: boolean;
  showMatchCheck?: boolean;
  isMatched?: boolean;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(({
  error,
  showStrength = false,
  showMatchCheck = false,
  isMatched = false,
  className = '',
  value = '',
  onFocus,
  onBlur,
  onHoverStart,
  onHoverEnd,
  ...props
}, ref) => {
  const [showPassword, setShowPassword] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const valStr = typeof value === 'string' ? value : '';

  // Calculate 3-segment strength:
  const getStrengthLevel = (pwd: string): number => {
    if (!pwd || pwd.length < 8) return 1;
    let score = 1;
    const hasLetters = /[a-zA-Z]/.test(pwd);
    const hasNumbers = /[0-9]/.test(pwd);
    const hasSymbols = /[^a-zA-Z0-9]/.test(pwd);
    const hasMixedCase = /[a-z]/.test(pwd) && /[A-Z]/.test(pwd);

    if ((hasLetters && hasNumbers) || (hasLetters && hasSymbols)) {
      score = 2; // Fair
    }
    if (pwd.length >= 10 && hasMixedCase && (hasNumbers || hasSymbols)) {
      score = 3; // Strong
    }
    return score;
  };

  const strength = showStrength ? getStrengthLevel(valStr) : 0;

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    onFocus?.(e);
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    onBlur?.(e);
  };

  return (
    <div className="w-full flex flex-col">
      <div
        className={`relative w-full h-[48px] rounded-[12px] bg-white transition-all duration-200 ${
          error
            ? 'border border-[#D9485F] ring-1 ring-[#D9485F]'
            : isFocused
            ? 'border border-[#111113] shadow-[0_0_0_4px_rgba(108,92,255,0.12)]'
            : 'border border-[#E2E2E7] hover:border-[#C8C8D0]'
        }`}
      >
        <div className="w-full h-full rounded-[12px] flex items-center pr-2.5">
          <input
            ref={ref}
            type={showPassword ? 'text' : 'password'}
            value={value}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onMouseEnter={() => onHoverStart?.('input')}
            onMouseLeave={onHoverEnd}
            className={`w-full h-full rounded-[12px] pl-4 pr-2 text-[15px] text-[#111113] placeholder-[#8A8A90] outline-none font-normal bg-transparent ${className}`}
            style={{
              cursor: 'text',
            }}
            aria-invalid={Boolean(error)}
            {...props}
          />

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Match checkmark icon */}
            <AnimatePresence>
              {showMatchCheck && isMatched && valStr.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.6 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.6 }}
                  transition={{ duration: 0.15 }}
                  className="w-5 h-5 rounded-full bg-[#EDE7FF] text-[#6C5CFF] flex items-center justify-center mr-0.5"
                  title="Passwords match"
                >
                  <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Show / Hide password toggle */}
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              onMouseEnter={() => onHoverStart?.('button')}
              onMouseLeave={onHoverEnd}
              aria-pressed={showPassword}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="p-1.5 text-[#8A8A90] hover:text-[#111113] rounded-lg transition-colors focus:outline-none focus:ring-1 focus:ring-[#111113]"
            >
              <AnimatePresence mode="wait" initial={false}>
                {showPassword ? (
                  <motion.div
                    key="eye-off"
                    initial={{ opacity: 0, rotate: -10 }}
                    animate={{ opacity: 1, rotate: 0 }}
                    exit={{ opacity: 0, rotate: 10 }}
                    transition={{ duration: 0.15 }}
                  >
                    <EyeOff className="w-4 h-4 stroke-[1.8]" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="eye"
                    initial={{ opacity: 0, rotate: 10 }}
                    animate={{ opacity: 1, rotate: 0 }}
                    exit={{ opacity: 0, rotate: -10 }}
                    transition={{ duration: 0.15 }}
                  >
                    <Eye className="w-4 h-4 stroke-[1.8]" />
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
          </div>
        </div>
      </div>

      {/* 3-segment strength bar and hint: ONLY appear once the user starts typing in password field */}
      {showStrength && valStr.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.15 }}
          className="flex flex-col gap-1 mt-1.5 px-1 overflow-hidden"
        >
          <div className="flex items-center gap-1.5 w-full">
            {[1, 2, 3].map((lvl) => {
              const isActive = strength >= lvl;
              return (
                <div
                  key={lvl}
                  className="flex-1 h-1 rounded-full bg-[#E5E5EB] overflow-hidden transition-all duration-300"
                >
                  <div
                    className={`h-full w-full rounded-full transition-all duration-300 ${
                      isActive
                        ? 'opacity-100 bg-gradient-to-r from-[#B33CF0] via-[#6C5CFF] to-[#3CC8FF]'
                        : 'opacity-0'
                    }`}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex items-center justify-between text-[11px] text-[#8A8A90] mt-0.5">
            <span>At least 8 characters</span>
            <span className="font-medium text-[#6C5CFF]">
              {strength === 1 ? 'Weak' : strength === 2 ? 'Fair' : 'Strong'}
            </span>
          </div>
        </motion.div>
      )}

      {/* Inline error message with gentle 150ms fade-slide */}
      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="text-[12px] font-medium text-[#D9485F] mt-1 ml-1 select-none"
            aria-live="polite"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
});

PasswordField.displayName = 'PasswordField';
