import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { RobotCompanion } from '../RobotCompanion.tsx';
import { HexBackground } from '../HexBackground.tsx';
import { authContent } from '../../content.ts';

interface AuthShowcaseProps {
  clientX: number;
  clientY: number;
  isIdle: boolean;
  isSuccess?: boolean;
}

export const AuthShowcase: React.FC<AuthShowcaseProps> = ({
  clientX,
  clientY,
  isIdle,
  isSuccess = false,
}) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const isReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const slides = authContent.showcase.slides;
  const durationMs = authContent.showcase.durationMs || 5000;

  // Auto-advance slides every 5s
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    }, durationMs);

    return () => clearInterval(timer);
  }, [slides.length, durationMs]);

  return (
    <div
      className="relative w-full h-full rounded-[20px] bg-[#ECECEE] overflow-hidden flex flex-col justify-between items-center select-none"
      style={{
        boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.7)',
      }}
    >
      {/* 1. Soft Embossed Hex Background at ~60% opacity */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-60">
        <HexBackground pointerX={0} pointerY={0} />
      </div>

      {/* 2. Gentle Vignette toward the panel edges */}
      <div
        className="absolute inset-0 pointer-events-none rounded-[20px]"
        style={{
          background:
            'radial-gradient(ellipse at 50% 45%, transparent 40%, rgba(220, 220, 224, 0.45) 85%, rgba(200, 200, 206, 0.6) 100%)',
        }}
      />

      {/* 3. Center Robot Area: centered slightly above middle, 62% width */}
      <div className="relative z-10 w-full flex-1 flex flex-col items-center justify-center pt-8 pb-2">
        {/* Drop-in animation on open + Happy hop on success */}
        <motion.div
          initial={
            isReducedMotion ? { opacity: 0 } : { opacity: 0, y: -40, scale: 0.95 }
          }
          animate={
            isSuccess && !isReducedMotion
              ? {
                  opacity: 1,
                  y: [0, -14, 0],
                  scale: 1,
                  transition: {
                    y: { duration: 0.6, ease: 'easeInOut' },
                  },
                }
              : {
                  opacity: 1,
                  y: 0,
                  scale: 1,
                }
          }
          transition={{
            duration: 0.8,
            ease: [0.22, 1, 0.36, 1],
            delay: 0.15,
          }}
          className="flex flex-col items-center justify-center pointer-events-auto"
        >
          <RobotCompanion
            size={270}
            calm={false}
            clientX={clientX}
            clientY={clientY}
            isIdle={isIdle}
          />
        </motion.div>
      </div>

      {/* 4. Caption Area at Bottom */}
      <motion.div
        initial={isReducedMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="relative z-10 w-full px-8 pb-8 flex flex-col items-center text-center"
      >
        <div className="h-[90px] flex flex-col items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentSlide}
              initial={
                isReducedMotion
                  ? { opacity: 0 }
                  : { opacity: 0, y: 10, filter: 'blur(4px)' }
              }
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={
                isReducedMotion
                  ? { opacity: 0 }
                  : { opacity: 0, y: -10, filter: 'blur(4px)' }
              }
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="flex flex-col items-center"
            >
              <p className="text-[17px] sm:text-[18px] font-medium text-[#111113] leading-snug max-w-sm">
                "{slides[currentSlide].quote}"
              </p>
              <span className="text-[12px] font-semibold text-[#8A8A90] tracking-wider uppercase mt-2">
                {slides[currentSlide].label}
              </span>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Pagination Dots */}
        <div className="flex items-center gap-1.5 mt-4" role="tablist" aria-label="Showcase slides">
          {slides.map((_, idx) => {
            const isActive = idx === currentSlide;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentSlide(idx)}
                aria-label={`Go to slide ${idx + 1}`}
                aria-selected={isActive}
                role="tab"
                className={`h-1.5 rounded-full transition-all duration-300 overflow-hidden relative cursor-pointer ${
                  isActive ? 'w-7 bg-[#111113]' : 'w-2 bg-[#D1D1D6] hover:bg-[#B0B0B8]'
                }`}
              >
                {isActive && (
                  <motion.div
                    key={`bar-${currentSlide}`}
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{
                      duration: durationMs / 1000,
                      ease: 'linear',
                    }}
                    className="h-full bg-gradient-to-r from-[#6C5CFF] to-[#3CC8FF] rounded-full"
                  />
                )}
              </button>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
};
