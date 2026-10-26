import React, { forwardRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface TextFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(({
  error,
  className = '',
  onFocus,
  onBlur,
  onHoverStart,
  onHoverEnd,
  ...props
}, ref) => {
  const [isFocused, setIsFocused] = useState(false);

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
        <input
          ref={ref}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onMouseEnter={() => onHoverStart?.('input')}
          onMouseLeave={onHoverEnd}
          className={`w-full h-full rounded-[12px] px-4 text-[15px] text-[#111113] placeholder-[#8A8A90] outline-none font-normal bg-transparent ${className}`}
          style={{
            cursor: 'text',
          }}
          aria-invalid={Boolean(error)}
          {...props}
        />
      </div>

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

TextField.displayName = 'TextField';
