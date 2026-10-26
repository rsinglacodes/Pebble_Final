import React, { useEffect, useRef, useState } from 'react';
import { featuresContent } from '../../content.ts';

interface TileYourCodeProps {
  className?: string;
}

export const TileYourCode: React.FC<TileYourCodeProps> = ({ className = '' }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // 6 code lines with muted syntax highlighting using only purple, blue, grey
  const codeLines = [
    { text: 'function solve(nodes) {', color: '#6C5CFF' },
    { text: '  let map = new Map();', color: '#71717A' },
    { text: '  for (let n of nodes) {', color: '#3B82F6' },
    { text: '    if (map.has(n.val))', color: '#8B5CF6' },
    { text: '      return n.link();', color: '#2563EB' },
    { text: '  }', color: '#6C5CFF' },
  ];

  const [visibleLinesCount, setVisibleLinesCount] = useState(1);
  const [activeExecLine, setActiveExecLine] = useState(-1);

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

  // Slowly typing lines (2 lines per sec) then stepping execution line
  useEffect(() => {
    if (!isVisible) return;

    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step <= 6) {
        setVisibleLinesCount(step);
        setActiveExecLine(-1);
      } else if (step <= 12) {
        setActiveExecLine((step - 7) % 6);
      } else {
        step = 0;
        setVisibleLinesCount(1);
        setActiveExecLine(-1);
      }
    }, 600);

    return () => clearInterval(interval);
  }, [isVisible]);

  return (
    <div
      ref={containerRef}
      className={`relative rounded-[28px] overflow-hidden select-none bg-gradient-to-br from-[#EAE4FF] via-[#E2E8FF] to-[#DCE6FF] p-4 flex flex-col justify-between shadow-[0_10px_30px_rgba(108,92,255,0.06)] ${className}`}
    >
      {/* Blurred pastel mesh blobs */}
      <div className="absolute top-0 right-0 w-28 h-28 rounded-full bg-[#DDD6FE] blur-2xl opacity-75 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-28 h-28 rounded-full bg-[#BAE6FD] blur-2xl opacity-70 pointer-events-none" />

      {/* Mini Code Window */}
      <div className="w-full bg-white/85 backdrop-blur-md rounded-2xl p-3 border border-white shadow-[0_6px_20px_rgba(108,92,255,0.08)] flex flex-col gap-2 z-10">
        {/* 3 tiny window dots */}
        <div className="flex items-center gap-1.5 pb-1 border-b border-gray-100">
          <div className="w-2 h-2 rounded-full bg-[#D1D5DB]" />
          <div className="w-2 h-2 rounded-full bg-[#D1D5DB]" />
          <div className="w-2 h-2 rounded-full bg-[#D1D5DB]" />
          <span className="text-[9px] font-mono text-gray-400 ml-2">solution.js</span>
        </div>

        {/* 6 lines of code */}
        <div className="font-mono text-[10px] leading-relaxed flex flex-col gap-0.5">
          {codeLines.map((line, idx) => {
            const isShown = idx < visibleLinesCount;
            const isExecuting = idx === activeExecLine;

            return (
              <div
                key={idx}
                className={`flex items-center gap-2 px-1.5 py-0.5 rounded transition-all duration-300 ${
                  isExecuting
                    ? 'bg-[#EDE7FF] border-l-2 border-[#6C5CFF]'
                    : 'border-l-2 border-transparent'
                }`}
                style={{ opacity: isShown ? 1 : 0 }}
              >
                <span className="text-[9px] text-gray-300 w-3">{idx + 1}</span>
                <span
                  style={{
                    color: line.color,
                    fontWeight: isExecuting ? 600 : 400,
                  }}
                >
                  {line.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Chip "Your code" at bottom left */}
      <div className="z-10 flex items-center pt-2">
        <span className="px-2.5 py-1 rounded-full text-[10px] sm:text-[11px] font-medium bg-white/70 backdrop-blur-xs text-[#14121F] shadow-2xs border border-white/60">
          {featuresContent.tiles.yourCode.chip}
        </span>
      </div>
    </div>
  );
};
