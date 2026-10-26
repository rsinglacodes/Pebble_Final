import React from 'react';
import { motion } from 'motion/react';

interface SplitTextProps {
  line1: string;
  line2: string;
  isVisible: boolean;
  className?: string;
}

export const SplitText: React.FC<SplitTextProps> = ({
  line1,
  line2,
  isVisible,
  className = '',
}) => {
  const isReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderLine = (text: string, lineIndex: number, startCharIndex: number) => {
    return (
      <span className="block overflow-hidden leading-[1.05]">
        {text.split('').map((char, charIdx) => {
          const globalCharIndex = startCharIndex + charIdx;
          if (isReducedMotion) {
            return (
              <span key={charIdx} className="inline-block">
                {char === ' ' ? '\u00A0' : char}
              </span>
            );
          }

          return (
            <span key={charIdx} className="inline-block overflow-hidden align-top">
              <motion.span
                className="inline-block"
                initial={{ y: '110%' }}
                animate={isVisible ? { y: '0%' } : { y: '110%' }}
                transition={{
                  duration: 0.9,
                  delay: globalCharIndex * 0.028,
                  ease: [0.16, 1, 0.3, 1],
                }}
              >
                {char === ' ' ? '\u00A0' : char}
              </motion.span>
            </span>
          );
        })}
      </span>
    );
  };

  return (
    <h2 className={`font-semibold tracking-[-0.03em] text-[#111113] select-none ${className}`}>
      {renderLine(line1, 0, 0)}
      {renderLine(line2, 1, line1.length)}
    </h2>
  );
};
