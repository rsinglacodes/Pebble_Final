import React from 'react';
import { siteContent, defaultColors } from '../content.ts';

interface NavProps {
  activeLinkId: string;
  onSelectLink: (id: string) => void;
  onInteractiveHoverStart: (label?: string) => void;
  onInteractiveHoverEnd: () => void;
  onOpenAuth?: () => void;
}

export const Nav: React.FC<NavProps> = ({
  activeLinkId,
  onSelectLink,
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
  onOpenAuth,
}) => {
  return (
    <nav className="w-full flex items-center justify-between px-6 sm:px-10 md:px-14 py-6 md:py-8 z-30 select-none">
      {/* Left: Brand Logo & Wordmark */}
      <div
        className="flex items-center gap-2.5 group cursor-pointer"
        onMouseEnter={() => onInteractiveHoverStart('logo')}
        onMouseLeave={onInteractiveHoverEnd}
      >
        {/* Organic Pebble logo mark with smooth stone contour and gem gradient */}
        <div
          className="relative w-8 h-7 sm:w-9 sm:h-8 rounded-[48%_52%_68%_32%_/_42%_44%_56%_58%] p-[2.5px] transition-all duration-500 ease-out shadow-sm group-hover:scale-105"
          style={{
            background: 'linear-gradient(135deg, #8B5CF6 0%, #6366F1 45%, #06B6D4 100%)',
          }}
        >
          <div className="w-full h-full bg-[#121217] rounded-[46%_54%_66%_34%_/_40%_42%_58%_60%] flex items-center justify-center gap-1.5 px-1 shadow-inner overflow-hidden relative">
            {/* Pebble inner soft highlight */}
            <div className="absolute -top-1 -left-1 w-3 h-3 bg-white/25 rounded-full blur-[2px]" />
            <span className="w-1.5 h-2.5 bg-gradient-to-b from-white to-[#C7D2FE] rounded-full transition-transform duration-300" />
            <span className="w-1.5 h-2.5 bg-gradient-to-b from-white to-[#A5F3FC] rounded-full transition-transform duration-300" />
          </div>
        </div>

        <span className="text-xl sm:text-2xl font-bold tracking-tight text-[#111113]">
          {siteContent.brand.name}
        </span>
      </div>

      {/* Center: Navigation Links (desktop) */}
      <div
        className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all duration-300"
        style={{
          background: 'rgba(255, 255, 255, 0.65)',
          backdropFilter: 'blur(16px) saturate(140%)',
          WebkitBackdropFilter: 'blur(16px) saturate(140%)',
          border: '1px solid rgba(255, 255, 255, 0.85)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.9)',
        }}
      >
        {siteContent.navigation.links.map((link) => {
          const isActive = activeLinkId === link.id;
          return (
            <button
              key={link.id}
              onClick={() => onSelectLink(link.id)}
              onMouseEnter={() => onInteractiveHoverStart('link')}
              onMouseLeave={onInteractiveHoverEnd}
              className={`px-4 py-1.5 rounded-full text-[12px] sm:text-[13px] font-medium transition-all duration-300 capitalize ${
                isActive
                  ? 'bg-[#111113] text-white shadow-xs'
                  : 'text-[#55555D] hover:text-[#111113] hover:bg-black/5'
              }`}
            >
              {link.label}
            </button>
          );
        })}
      </div>

      {/* Right: Adopt Me Button (fixed black background, no color change) */}
      <div className="flex items-center">
        <button
          onClick={onOpenAuth}
          onMouseEnter={() => onInteractiveHoverStart('adopt')}
          onMouseLeave={onInteractiveHoverEnd}
          className="px-5 py-2 sm:px-6 sm:py-2.5 rounded-full text-xs sm:text-sm font-semibold tracking-wide text-white bg-[#111113] transition-all duration-300 shadow-sm hover:shadow-md hover:scale-[1.03] active:scale-[0.98] cursor-pointer"
        >
          {siteContent.navigation.cta}
        </button>
      </div>
    </nav>
  );
};
