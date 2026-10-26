import React, { useEffect, useRef, useState } from 'react';
import { featuresContent } from '../../content.ts';

interface TileSortingBarsProps {
  className?: string;
}

export const TileSortingBars: React.FC<TileSortingBarsProps> = ({ className = '' }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // 8 bars of different heights (percentages)
  const [bars, setBars] = useState([35, 75, 20, 90, 50, 65, 30, 85]);
  const [comparing, setComparing] = useState<[number, number] | null>([0, 1]);

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

  // Slow gentle bubble sort step loop
  useEffect(() => {
    if (!isVisible) return;

    let i = 0;
    let j = 0;
    let currentArray = [35, 75, 20, 90, 50, 65, 30, 85];

    const timer = setInterval(() => {
      if (i >= currentArray.length - 1) {
        // Reset after complete cycle
        currentArray = [35, 75, 20, 90, 50, 65, 30, 85];
        i = 0;
        j = 0;
        setBars([...currentArray]);
        setComparing([0, 1]);
        return;
      }

      setComparing([j, j + 1]);

      if (currentArray[j] > currentArray[j + 1]) {
        // Swap
        const temp = currentArray[j];
        currentArray[j] = currentArray[j + 1];
        currentArray[j + 1] = temp;
        setBars([...currentArray]);
      }

      j++;
      if (j >= currentArray.length - 1 - i) {
        j = 0;
        i++;
      }
    }, 1100);

    return () => clearInterval(timer);
  }, [isVisible]);

  return (
    <div
      ref={containerRef}
      className={`relative rounded-[28px] overflow-hidden select-none bg-gradient-to-br from-[#D8F0FF] via-[#E2ECFF] to-[#EDE7FF] p-4 flex flex-col justify-between shadow-[0_10px_30px_rgba(108,92,255,0.06)] ${className}`}
    >
      {/* Blurred pastel mesh blobs */}
      <div className="absolute -top-4 right-2 w-32 h-32 rounded-full bg-[#BAE6FD] blur-2xl opacity-75 pointer-events-none" />
      <div className="absolute -bottom-4 -left-4 w-32 h-32 rounded-full bg-[#DDD6FE] blur-2xl opacity-70 pointer-events-none" />

      {/* Top chip "Step by step" at top right */}
      <div className="z-10 flex items-center justify-end">
        <span className="px-2.5 py-1 rounded-full text-[10px] sm:text-[11px] font-medium bg-white/70 backdrop-blur-xs text-[#14121F] shadow-2xs border border-white/60">
          {featuresContent.tiles.sortingBars.chip}
        </span>
      </div>

      {/* Sorting Bars Container */}
      <div className="relative my-auto flex items-end justify-center gap-1.5 sm:gap-2 h-24 sm:h-28 z-10 px-2">
        {bars.map((h, idx) => {
          const isComparing = comparing && (comparing[0] === idx || comparing[1] === idx);

          return (
            <div
              key={idx}
              className="w-3 sm:w-3.5 rounded-full transition-all duration-500 ease-out flex flex-col justify-end"
              style={{
                height: `${h}%`,
                background: isComparing
                  ? 'linear-gradient(to top, #6C5CFF, #B33CF0)'
                  : 'linear-gradient(to top, rgba(108,92,255,0.35), rgba(60,200,255,0.45))',
                boxShadow: isComparing
                  ? '0 0 12px rgba(108, 92, 255, 0.5)'
                  : 'none',
                transform: isComparing ? 'scaleY(1.04)' : 'scaleY(1)',
              }}
            />
          );
        })}
      </div>

      {/* Bottom Subtle Status */}
      <div className="z-10 text-center text-[10px] text-[#71717A] font-mono">
        sorting in-place • swap trace
      </div>
    </div>
  );
};
