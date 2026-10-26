import React, { useEffect, useRef, useState } from 'react';
import { featuresContent } from '../../content.ts';

interface TileTwoPointersProps {
  className?: string;
}

export const TileTwoPointers: React.FC<TileTwoPointersProps> = ({ className = '' }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  const numbers = [1, 3, 4, 6, 8, 11];
  const [leftIdx, setLeftIdx] = useState(0);
  const [rightIdx, setRightIdx] = useState(5);
  const [isMeeting, setIsMeeting] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.35 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Step pointers inward every ~1.4s
  useEffect(() => {
    if (!isVisible) return;

    const timer = setInterval(() => {
      setLeftIdx((prevL) => {
        setRightIdx((prevR) => {
          if (prevL + 1 >= prevR) {
            setIsMeeting(true);
            setTimeout(() => {
              setIsMeeting(false);
              setLeftIdx(0);
              setRightIdx(5);
            }, 1200);
            return prevR;
          }
          return prevR - 1;
        });
        return prevL + 1;
      });
    }, 1400);

    return () => clearInterval(timer);
  }, [isVisible]);

  return (
    <div
      ref={containerRef}
      className={`relative rounded-[28px] overflow-hidden select-none bg-gradient-to-br from-[#F4DCFF] via-[#EAE2FF] to-[#DDE3FF] p-4 flex flex-col justify-between shadow-[0_10px_30px_rgba(108,92,255,0.06)] ${className}`}
    >
      {/* Blurred pastel mesh blobs */}
      <div className="absolute top-2 -right-4 w-28 h-28 rounded-full bg-[#E9D5FF] blur-2xl opacity-75 pointer-events-none" />
      <div className="absolute -bottom-4 left-2 w-28 h-28 rounded-full bg-[#C7D2FE] blur-2xl opacity-70 pointer-events-none" />

      {/* Top chip "Two pointers" */}
      <div className="z-10 flex items-center">
        <span className="px-2.5 py-1 rounded-full text-[10px] sm:text-[11px] font-medium bg-white/70 backdrop-blur-xs text-[#14121F] shadow-2xs border border-white/60">
          {featuresContent.tiles.twoPointers.chip}
        </span>
      </div>

      {/* Row of 6 Number Cells with Pointers */}
      <div className="relative my-auto z-10 flex flex-col items-center gap-2 py-3">
        <div className="flex items-center gap-1.5 sm:gap-2">
          {numbers.map((num, i) => {
            const isLeft = i === leftIdx;
            const isRight = i === rightIdx;
            const isTarget = isLeft || isRight;

            return (
              <div
                key={i}
                className={`w-7 h-8 sm:w-8 sm:h-9 rounded-xl flex items-center justify-center font-mono text-xs sm:text-sm font-semibold transition-all duration-300 ${
                  isMeeting
                    ? 'bg-purple-200 text-purple-900 scale-105 shadow-sm'
                    : isTarget
                    ? 'bg-white text-[#6C5CFF] border-2 border-[#6C5CFF] -translate-y-1 shadow-md shadow-purple-500/15'
                    : 'bg-white/70 text-[#14121F] border border-white/80'
                }`}
              >
                {num}
              </div>
            );
          })}
        </div>

        {/* Pointer Indicators L & R */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {numbers.map((_, i) => {
            const isLeft = i === leftIdx;
            const isRight = i === rightIdx;

            return (
              <div
                key={`ptr-${i}`}
                className="w-7 sm:w-8 h-4 flex items-center justify-center text-[10px] font-bold font-mono transition-opacity duration-300"
              >
                {isLeft && (
                  <span className="px-1 rounded bg-[#6C5CFF] text-white text-[9px] shadow-xs animate-bounce">
                    L
                  </span>
                )}
                {isRight && !isLeft && (
                  <span className="px-1 rounded bg-[#3CC8FF] text-white text-[9px] shadow-xs animate-bounce">
                    R
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Target status indicator */}
      <div className="z-10 text-center text-[10px] text-[#71717A] font-mono">
        target: <span className="font-semibold text-[#6C5CFF]">10</span> (
        {numbers[leftIdx]} + {numbers[rightIdx]} ={' '}
        <span className="font-semibold">{numbers[leftIdx] + numbers[rightIdx]}</span>)
      </div>
    </div>
  );
};
