import React, { useEffect } from 'react';
import { motion } from 'motion/react';
import { authContent } from '../../content.ts';

interface SuccessViewProps {
  userName?: string;
  isSignUp?: boolean;
  onContinue: () => void;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const SuccessView: React.FC<SuccessViewProps> = ({
  userName,
  isSignUp = true,
  onContinue,
  onHoverStart,
  onHoverEnd,
}) => {
  // Auto-close after 1.6s
  useEffect(() => {
    const timer = setTimeout(() => {
      onContinue();
    }, 1600);
    return () => clearTimeout(timer);
  }, [onContinue]);

  const firstName = userName ? userName.trim().split(' ')[0] : '';
  const title = isSignUp && firstName
    ? authContent.success.signupTitle.replace('{name}', firstName)
    : authContent.success.loginTitle;

  return (
    <div className="w-full flex flex-col items-center justify-center py-6 text-center select-none">
      {/* Animated Checkmark in Gradient Circle */}
      <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
        {/* Soft background pulse glow */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#6C5CFF]/30 to-[#3CC8FF]/30 blur-lg animate-pulse" />

        <div className="relative w-16 h-16 rounded-full bg-gradient-to-tr from-[#B33CF0] via-[#6C5CFF] to-[#3CC8FF] flex items-center justify-center shadow-[0_8px_24px_rgba(108,92,255,0.3)]">
          <svg
            className="w-8 h-8 text-white"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <motion.path
              d="M5 13l4 4L19 7"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease: 'easeOut', delay: 0.15 }}
            />
          </svg>
        </div>
      </div>

      {/* Title */}
      <motion.h3
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="text-2xl font-bold tracking-tight text-[#111113]"
      >
        {title}
      </motion.h3>

      {/* Subtitle */}
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="text-[#8A8A90] text-sm mt-2 font-normal"
      >
        {authContent.success.subtitle}
      </motion.p>

      {/* Manual Continue Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.5 }}
        className="mt-6"
      >
        <button
          type="button"
          onClick={onContinue}
          onMouseEnter={() => onHoverStart?.('button')}
          onMouseLeave={onHoverEnd}
          className="text-xs font-semibold text-[#6C5CFF] hover:text-[#5241E0] hover:underline px-3 py-1.5 transition-colors focus:outline-none"
        >
          {authContent.success.continueButton} →
        </button>
      </motion.div>
    </div>
  );
};
