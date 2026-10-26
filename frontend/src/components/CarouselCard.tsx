import React, { useState, useEffect } from 'react';

interface CarouselCardProps {
  onInteractiveHoverStart: (label?: string) => void;
  onInteractiveHoverEnd: () => void;
}

export const CarouselCard: React.FC<CarouselCardProps> = ({
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
}) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const totalSlides = 3;

  // Auto-advance sideways slides every 4.2s (pauses on hover)
  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % totalSlides);
    }, 4200);
    return () => clearInterval(interval);
  }, [isPaused, totalSlides]);

  return (
    <div
      className="flex flex-col items-center select-none z-20"
      onMouseEnter={() => {
        setIsPaused(true);
        onInteractiveHoverStart('card');
      }}
      onMouseLeave={() => {
        setIsPaused(false);
        onInteractiveHoverEnd();
      }}
    >
      {/* The White Frosted Card Container */}
      <div className="relative w-[215px] sm:w-[250px] md:w-[270px] h-[135px] sm:h-[150px] md:h-[160px] bg-white rounded-2xl p-2 shadow-[0_12px_36px_rgba(0,0,0,0.06),0_2px_8px_rgba(0,0,0,0.03)] border border-black/5 flex flex-col justify-center items-center overflow-hidden transition-all duration-300 hover:shadow-[0_16px_40px_rgba(0,0,0,0.09)] hover:-translate-y-0.5">
        {/* Sideways Moving Slide Track */}
        <div
          className="w-full h-full flex transition-transform duration-500 ease-out will-change-transform"
          style={{
            transform: `translateX(-${activeIndex * 100}%)`,
          }}
        >
          {/* SLIDE 1: "while(!clear) { explain(); }" in Black Font */}
          <div className="w-full h-full shrink-0 flex items-center justify-center p-4 rounded-xl bg-gradient-to-br from-[#F7F5FE] via-[#FAF9FD] to-[#F1F4FF] border border-purple-100/60 relative overflow-hidden">
            <p className="font-mono text-xs sm:text-sm font-semibold tracking-tight text-center leading-snug text-[#111113]">
              while(!clear) &#123; explain(); &#125;
            </p>
          </div>

          {/* SLIDE 2: Connected Nodes Graph Structure */}
          <div className="w-full h-full shrink-0 flex items-center justify-center p-2 rounded-xl bg-gradient-to-br from-[#F8FAFC] via-[#F4F6FB] to-[#F7F5FE] border border-indigo-100/50 relative overflow-hidden">
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-full h-full max-h-[115px]" viewBox="0 0 220 100">
                <defs>
                  <linearGradient id="primaryNodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#8B5CF6" />
                    <stop offset="100%" stopColor="#6366F1" />
                  </linearGradient>
                </defs>

                {/* Connecting Graph Edges */}
                <line x1="45" y1="34" x2="110" y2="22" stroke="#818CF8" strokeWidth="2" strokeDasharray="3 2" className="animate-pulse" />
                <line x1="110" y1="22" x2="175" y2="34" stroke="#818CF8" strokeWidth="2" />
                <line x1="45" y1="34" x2="75" y2="78" stroke="#818CF8" strokeWidth="2" />
                <line x1="110" y1="22" x2="75" y2="78" stroke="#6366F1" strokeWidth="2.5" />
                <line x1="110" y1="22" x2="150" y2="75" stroke="#6366F1" strokeWidth="2.5" />
                <line x1="175" y1="34" x2="150" y2="75" stroke="#818CF8" strokeWidth="2" />
                <line x1="75" y1="78" x2="150" y2="75" stroke="#38BDF8" strokeWidth="2" strokeDasharray="4 2" />

                {/* Graph Nodes */}
                <g>
                  <circle cx="45" cy="34" r="11" fill="#FFFFFF" stroke="#8B5CF6" strokeWidth="2.5" />
                  <text x="45" y="38" textAnchor="middle" fill="#6D28D9" fontSize="10" fontWeight="bold" fontFamily="monospace">1</text>
                </g>
                <g>
                  <circle cx="110" cy="22" r="13" fill="url(#primaryNodeGrad)" stroke="#6366F1" strokeWidth="2" />
                  <text x="110" y="26" textAnchor="middle" fill="#FFFFFF" fontSize="11" fontWeight="bold" fontFamily="monospace">2</text>
                </g>
                <g>
                  <circle cx="175" cy="34" r="11" fill="#FFFFFF" stroke="#8B5CF6" strokeWidth="2.5" />
                  <text x="175" y="38" textAnchor="middle" fill="#6D28D9" fontSize="10" fontWeight="bold" fontFamily="monospace">3</text>
                </g>
                <g>
                  <circle cx="75" cy="78" r="11" fill="#FFFFFF" stroke="#06B6D4" strokeWidth="2.5" />
                  <text x="75" y="82" textAnchor="middle" fill="#0E7490" fontSize="10" fontWeight="bold" fontFamily="monospace">4</text>
                </g>
                <g>
                  <circle cx="150" cy="75" r="11" fill="#FFFFFF" stroke="#10B981" strokeWidth="2.5" />
                  <text x="150" y="79" textAnchor="middle" fill="#047857" fontSize="10" fontWeight="bold" fontFamily="monospace">5</text>
                </g>
              </svg>
            </div>
          </div>

          {/* SLIDE 3: "understand better" in Black Font */}
          <div className="w-full h-full shrink-0 flex items-center justify-center p-4 rounded-xl bg-gradient-to-br from-[#FAF8FF] via-[#F6F4FE] to-[#EFF6FF] border border-purple-100/60 relative overflow-hidden">
            <p className="text-lg sm:text-xl font-bold tracking-tight text-center capitalize leading-snug text-[#111113]">
              understand better
            </p>
          </div>
        </div>
      </div>

      {/* Pagination dots below for navigation */}
      <div className="mt-3 flex items-center justify-center gap-2">
        {[0, 1, 2].map((idx) => {
          const isActive = idx === activeIndex;
          return (
            <button
              key={idx}
              onClick={() => setActiveIndex(idx)}
              aria-label={`Go to slide ${idx + 1}`}
              className={`rounded-full transition-all duration-300 cursor-pointer ${
                isActive
                  ? 'w-5 h-1.5 bg-[#111113]'
                  : 'w-1.5 h-1.5 bg-[#C5C5CD] hover:bg-[#8E8E98]'
              }`}
            />
          );
        })}
      </div>
    </div>
  );
};
