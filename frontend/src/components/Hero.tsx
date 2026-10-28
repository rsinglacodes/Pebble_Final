import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { siteContent, defaultColors } from '../content.ts';

interface HeroProps {
  onInteractiveHoverStart: (label?: string) => void;
  onInteractiveHoverEnd: () => void;
  onOpenAuth?: () => void;
  isLoggedIn?: boolean;
  onOpenChatbot?: () => void;
}

export const Hero: React.FC<HeroProps> = ({
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
  onOpenAuth,
  isLoggedIn = false,
  onOpenChatbot,
}) => {
  const handleCtaClick = isLoggedIn ? (onOpenChatbot ?? onOpenAuth) : onOpenAuth;
  const ctaText = isLoggedIn ? 'Open chatbot' : siteContent.hero.cta;

  return (
    <div className="flex flex-col justify-center max-w-xl z-20 select-none">
      {/* 3-line Headline */}
      <h1 className="font-semibold tracking-[-0.03em] leading-[1.08] text-[#111113]">
        <span className="block" style={{ fontSize: '38.8944px' }}>{siteContent.hero.headline.line1}</span>
        <span
          className="block py-0.5"
          style={{
            fontSize: '43.8944px',
            backgroundImage: defaultColors.gradientCss,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {siteContent.hero.headline.line2}
        </span>
        <span className="block" style={{ fontSize: '38.8944px' }}>{siteContent.hero.headline.line3}</span>
      </h1>

      {/* Subtitle */}
      <p className="mt-4 sm:mt-5 text-[#8A8A90] text-sm sm:text-base leading-snug max-w-[340px] sm:max-w-[440px] font-normal">
        {siteContent.hero.subtitle}
      </p>

      {/* Hero CTA Button (always black, no color shift) */}
      <div className="mt-6 sm:mt-8 flex items-center">
        <button
          type="button"
          onClick={handleCtaClick}
          data-cursor="button"
          onMouseEnter={() => onInteractiveHoverStart(isLoggedIn ? 'chatbot-cta' : 'adopt-cta')}
          onMouseLeave={onInteractiveHoverEnd}
          className="group inline-flex items-center gap-1.5 px-6 sm:px-7 py-3 sm:py-3.5 rounded-full text-sm sm:text-base font-semibold text-white bg-[#111113] transition-all duration-300 shadow-sm hover:shadow-lg hover:scale-[1.03] active:scale-[0.98] cursor-pointer"
        >
          <span>{ctaText}</span>
          <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </button>
      </div>
    </div>
  );
};
