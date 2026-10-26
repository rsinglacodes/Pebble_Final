import React, { useMemo, useEffect, useRef } from 'react';
import { getPointer } from '../lib/pointerStore.ts';

interface HexBackgroundProps {
  pointerX?: number; // -1 to 1
  pointerY?: number; // -1 to 1
  isStatic?: boolean;
}

interface HexTileData {
  id: string;
  cx: number;
  cy: number;
  duration: number;
  delay: number;
  initialOpacity: number;
}

export const HexBackground: React.FC<HexBackgroundProps> = ({
  isStatic = false,
}) => {
  const layerRef = useRef<HTMLDivElement | null>(null);

  const tiles: HexTileData[] = useMemo(() => {
    const list: HexTileData[] = [];
    const rows = 24;
    const cols = 7;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cx = 7 + c * 14.5 + (r % 2 === 1 ? 7.25 : 0);
        const cy = 2 + r * 4.2;

        if ((r % 4 === 0 && (c === 0 || c === cols - 1)) && r > 2 && r < rows - 2) {
          continue;
        }

        const duration = 6.5 + ((r * 7 + c * 13) % 40) / 10;
        const delay = -((r * 11 + c * 17) % 100) / 10;
        const initialOpacity = 0.35 + (((r + c) * 3) % 6) * 0.1;

        list.push({
          id: `hex-${r}-${c}`,
          cx,
          cy,
          duration,
          delay,
          initialOpacity,
        });
      }
    }
    return list;
  }, []);

  const dustDots = useMemo(() => {
    const dots = [];
    const count = 28;
    for (let i = 0; i < count; i++) {
      const x = `${(i * 37) % 92 + 4}%`;
      const y = `${(i * 3.4) % 96 + 2}%`;
      const size = 2 + (i % 3);
      const opacity = 0.2 + ((i * 7) % 15) / 100;
      dots.push({ x, y, size, opacity });
    }
    return dots;
  }, []);

  // Smooth rAF parallax layer without React re-renders
  useEffect(() => {
    if (isStatic) return;
    let animId: number;
    let curX = 0;
    let curY = 0;

    const loop = () => {
      const p = getPointer();
      curX += (-p.x * 12 - curX) * 0.08;
      curY += (-p.y * 12 - curY) * 0.08;
      if (layerRef.current) {
        layerRef.current.style.transform = `translate3d(${curX.toFixed(2)}px, ${curY.toFixed(2)}px, 0)`;
      }
      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, [isStatic]);

  const hexPath =
    'M 60,6 C 64,3.7 72,8 75,10 L 111,31 C 115,33 117,37 117,42 L 117,96 C 117,101 115,105 111,107 L 75,128 C 72,130 64,134 60,132 C 56,134 48,130 45,128 L 9,107 C 5,105 3,101 3,96 L 3,42 C 3,37 5,33 9,31 L 45,10 C 48,8 56,3.7 60,6 Z';

  return (
    <div
      className="absolute inset-0 overflow-hidden pointer-events-none rounded-[28px]"
      aria-hidden="true"
    >
      <div
        ref={layerRef}
        className="w-full h-full relative will-change-transform"
        style={{
          transform: 'translate3d(0px, 0px, 0)',
        }}
      >
        {tiles.map((tile) => (
          <div
            key={tile.id}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 will-change-transform"
            style={{
              left: `${tile.cx}%`,
              top: `${tile.cy}%`,
              width: 'clamp(110px, 13vw, 175px)',
              aspectRatio: '120 / 138',
              animation: isStatic
                ? 'none'
                : `hexBreathe ${tile.duration}s ease-in-out infinite alternate`,
              animationDelay: `${tile.delay}s`,
              opacity: isStatic ? 0.35 : undefined,
            }}
          >
            <svg
              viewBox="0 0 120 138"
              className="w-full h-full"
              style={{
                filter:
                  'drop-shadow(-3px -3px 6px rgba(255, 255, 255, 0.95)) drop-shadow(4px 5px 8px rgba(180, 184, 195, 0.3))',
              }}
            >
              <path
                d={hexPath}
                fill="#F1F1F3"
                stroke="rgba(255, 255, 255, 0.75)"
                strokeWidth="1.2"
              />
            </svg>
          </div>
        ))}

        {!isStatic &&
          dustDots.map((dot, i) => (
            <div
              key={`dot-${i}`}
              className="absolute rounded-full bg-[#9E9EA8]"
              style={{
                left: dot.x,
                top: dot.y,
                width: `${dot.size}px`,
                height: `${dot.size}px`,
                opacity: dot.opacity,
              }}
            />
          ))}
      </div>

      <style>{`
        @keyframes hexBreathe {
          0% {
            opacity: 0.28;
            transform: translate(-50%, -50%) scale(0.975);
          }
          50% {
            opacity: 0.9;
            transform: translate(-50%, -50%) scale(1.02);
          }
          100% {
            opacity: 0.35;
            transform: translate(-50%, -50%) scale(0.985);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .will-change-transform {
            animation: none !important;
            transform: translate(-50%, -50%) scale(1) !important;
          }
        }
      `}</style>
    </div>
  );
};
