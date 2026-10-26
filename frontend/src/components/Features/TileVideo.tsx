import React, { useEffect, useRef, useState } from 'react';
import { Play } from 'lucide-react';
import { featuresContent } from '../../content.ts';

interface TileVideoProps {
  className?: string;
}

export const TileVideo: React.FC<TileVideoProps> = ({ className = '' }) => {
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

  return (
    <div
      ref={containerRef}
      className={`relative rounded-[28px] overflow-hidden select-none bg-gradient-to-br from-[#E6DCFF] via-[#E1E8FF] to-[#D8F0FF] p-4 flex flex-col justify-between shadow-[0_10px_30px_rgba(108,92,255,0.06)] ${className}`}
    >
      {/* 2-3 heavily blurred pastel color blobs inside */}
      <div className="absolute -top-6 -right-6 w-28 h-28 rounded-full bg-[#C7D2FE] blur-2xl opacity-70 pointer-events-none" />
      <div className="absolute -bottom-6 -left-6 w-28 h-28 rounded-full bg-[#DDD6FE] blur-2xl opacity-75 pointer-events-none" />

      {/* Top chip "Walkthrough" */}
      <div className="z-10 flex items-center">
        <span className="px-2.5 py-1 rounded-full text-[10px] sm:text-[11px] font-medium bg-white/70 backdrop-blur-xs text-[#14121F] shadow-2xs border border-white/60">
          {featuresContent.tiles.video.chip}
        </span>
      </div>

      {/* Center Frosted Glass Circular Play Button with Pulsing Ripple */}
      <div className="relative my-auto flex items-center justify-center py-4 z-10">
        {/* Pulsing ripple ring */}
        <div
          className={`absolute w-16 h-16 sm:w-20 sm:h-20 rounded-full border border-purple-400/40 pointer-events-none transition-transform duration-1000 ${
            isVisible ? 'animate-ping opacity-40' : 'opacity-0'
          }`}
          style={{ animationDuration: '4s' }}
        />

        {/* Circular play button */}
        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-white/60 backdrop-blur-md border border-white/80 shadow-[0_8px_24px_rgba(108,92,255,0.18)] flex items-center justify-center transition-transform duration-300 hover:scale-105">
          <Play className="w-6 h-6 text-[#6C5CFF] fill-[#6C5CFF] ml-1" />
        </div>
      </div>

      {/* Bottom Scrub Bar */}
      <div className="z-10 w-full flex flex-col gap-1.5 pb-1">
        <div className="w-full h-1.5 bg-white/50 backdrop-blur-xs rounded-full overflow-hidden relative">
          <div
            className={`h-full rounded-full transition-all ease-linear ${
              isVisible ? 'animate-videoScrub' : ''
            }`}
            style={{
              background: 'linear-gradient(90deg, #B33CF0, #6C5CFF, #3CC8FF)',
            }}
          />
        </div>
      </div>

      <style>{`
        @keyframes videoScrub {
          0% {
            width: 0%;
          }
          100% {
            width: 100%;
          }
        }
        .animate-videoScrub {
          animation: videoScrub 7s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }
      `}</style>
    </div>
  );
};
