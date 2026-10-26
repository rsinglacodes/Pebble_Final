import React, { useEffect, useRef, useState } from 'react';
import { featuresContent } from '../../content.ts';

interface TileAlgorithmsProps {
  className?: string;
}

export const TileAlgorithms: React.FC<TileAlgorithmsProps> = ({ className = '' }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

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

  // 5 overlapping glossy chips
  const chips = [
    {
      id: 1,
      glyph: '{ }',
      bg: 'linear-gradient(135deg, rgba(230,220,255,0.92) 0%, rgba(210,195,255,0.85) 100%)',
      border: 'rgba(255,255,255,0.85)',
      textColor: '#6C5CFF',
      size: 'w-24 h-24 sm:w-28 sm:h-28',
      offsetY: -65,
      offsetX: -10,
      zIndex: 1,
      rotate: -4,
      animDuration: '7s',
      delay: '0s',
    },
    {
      id: 2,
      glyph: 'O(n)',
      bg: 'linear-gradient(135deg, rgba(216,240,255,0.92) 0%, rgba(186,225,255,0.85) 100%)',
      border: 'rgba(255,255,255,0.85)',
      textColor: '#0284C7',
      size: 'w-26 h-26 sm:w-30 sm:h-30',
      offsetY: -30,
      offsetX: 18,
      zIndex: 2,
      rotate: 3,
      animDuration: '8s',
      delay: '-1.5s',
    },
    {
      id: 3,
      glyph: '↗',
      bg: 'linear-gradient(135deg, rgba(244,220,255,0.92) 0%, rgba(226,195,255,0.85) 100%)',
      border: 'rgba(255,255,255,0.85)',
      textColor: '#A855F7',
      size: 'w-28 h-28 sm:w-32 sm:h-32',
      offsetY: 8,
      offsetX: -22,
      zIndex: 3,
      rotate: -2,
      animDuration: '7.5s',
      delay: '-3s',
    },
    {
      id: 4,
      glyph: '[ ]',
      bg: 'linear-gradient(135deg, rgba(221,227,255,0.92) 0%, rgba(195,205,255,0.85) 100%)',
      border: 'rgba(255,255,255,0.85)',
      textColor: '#4F46E5',
      size: 'w-26 h-26 sm:w-30 sm:h-30',
      offsetY: 45,
      offsetX: 14,
      zIndex: 4,
      rotate: 4,
      animDuration: '8.5s',
      delay: '-4.2s',
    },
    {
      id: 5,
      glyph: '</>',
      bg: 'linear-gradient(135deg, rgba(200,210,255,0.95) 0%, rgba(175,190,255,0.9) 100%)',
      border: 'rgba(255,255,255,0.9)',
      textColor: '#4338CA',
      size: 'w-24 h-24 sm:w-28 sm:h-28',
      offsetY: 80,
      offsetX: -6,
      zIndex: 5,
      rotate: -1,
      animDuration: '6.8s',
      delay: '-2.2s',
    },
  ];

  return (
    <div
      ref={containerRef}
      className={`relative rounded-[28px] overflow-hidden select-none bg-gradient-to-br from-[#EDE7FF] via-[#E8E1FD] to-[#DDE5FF] p-4 flex flex-col justify-between shadow-[0_12px_36px_rgba(108,92,255,0.08)] ${className}`}
      style={{
        isolation: 'isolate',
        contain: 'paint',
      }}
    >
      {/* Blurred pastel mesh blobs */}
      <div className="absolute top-10 left-4 w-36 h-36 rounded-full bg-[#DDD6FE] blur-3xl opacity-80 pointer-events-none" />
      <div className="absolute bottom-8 right-4 w-40 h-40 rounded-full bg-[#BAE6FD] blur-3xl opacity-75 pointer-events-none" />

      {/* Top chip "Algorithms" */}
      <div className="z-10 flex items-center">
        <span className="px-3 py-1 rounded-full text-[10px] sm:text-[11px] font-medium bg-white/70 backdrop-blur-xs text-[#14121F] shadow-2xs border border-white/60">
          {featuresContent.tiles.algorithms.chip}
        </span>
      </div>

      {/* Center Stack of 5 Overlapping Glossy Chips - strictly overflow-hidden */}
      <div className="relative my-auto flex items-center justify-center h-52 sm:h-64 z-10 overflow-hidden">
        {chips.map((chip) => (
          <div
            key={chip.id}
            className={`absolute rounded-[22px] sm:rounded-[26px] ${chip.size} flex items-center justify-center font-mono font-bold text-base sm:text-lg backdrop-blur-md will-change-transform ${
              isVisible ? 'animate-chipBob' : ''
            }`}
            style={{
              background: chip.bg,
              border: `1.5px solid ${chip.border}`,
              color: chip.textColor,
              boxShadow:
                'inset 0 1.5px 1px rgba(255, 255, 255, 0.85), inset 0 -2px 4px rgba(0, 0, 0, 0.05), 0 8px 24px rgba(108, 92, 255, 0.12)',
              transform: `translate3d(${chip.offsetX}px, ${chip.offsetY}px, 0) rotate(${chip.rotate}deg)`,
              zIndex: chip.zIndex,
              animationDuration: chip.animDuration,
              animationDelay: chip.delay,
            }}
          >
            {/* Glossy corner sheen */}
            <div className="absolute top-1 left-2 w-8 h-4 bg-white/40 rounded-full blur-[1px] pointer-events-none" />
            <span>{chip.glyph}</span>
          </div>
        ))}
      </div>

      {/* Bottom Subtle Badge */}
      <div className="z-10 text-center text-[10px] text-[#71717A] font-medium">
        5 core algorithmic patterns
      </div>

      <style>{`
        @keyframes chipBob {
          0%, 100% {
            transform: translateY(0px) rotate(0deg);
          }
          50% {
            transform: translateY(-6px) rotate(2deg);
          }
        }
      `}</style>
    </div>
  );
};
