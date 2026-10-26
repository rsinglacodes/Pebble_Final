import React from 'react';
import { ArrowUpRight, Check, Play } from 'lucide-react';
import { featuresContent } from '../../content.ts';

export type UiCardType = 'visualize' | 'leetcode' | 'complexity';

interface UiCardProps {
  type: UiCardType;
  className?: string;
  onHoverStart?: () => void;
  onHoverEnd?: () => void;
}

export const UiCard: React.FC<UiCardProps> = ({
  type,
  className = '',
  onHoverStart,
  onHoverEnd,
}) => {
  return (
    <div
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
      className={`bg-[#FAFAFB] rounded-[14px] border-2 border-[#14121F] shadow-[5px_5px_0_#14121F] p-3 sm:p-3.5 select-none transition-transform duration-200 hover:-translate-y-0.5 ${className}`}
    >
      {/* 1. VISUALIZE UI CARD */}
      {type === 'visualize' && (
        <div className="flex items-center gap-3">
          {/* Light-lavender rounded square with play icon */}
          <div className="w-10 h-10 rounded-xl bg-[#EDE7FF] border border-[#D5C9FF] flex items-center justify-center shrink-0">
            <Play className="w-4 h-4 text-[#6C5CFF] fill-[#6C5CFF] ml-0.5" />
          </div>
          <div className="flex flex-col text-left">
            <div className="text-xs sm:text-[13px] font-semibold text-[#14121F] tracking-tight">
              {featuresContent.uiCards.visualize.title}
            </div>
            <div className="text-[10px] sm:text-[11px] text-[#71717A] leading-tight mt-0.5">
              <span>{featuresContent.uiCards.visualize.subtext1}</span>
              <br />
              <span>{featuresContent.uiCards.visualize.subtext2}</span>
            </div>
          </div>
        </div>
      )}

      {/* 2. LEETCODE PROBLEM UI CARD */}
      {type === 'leetcode' && (
        <div className="flex flex-col gap-2 min-w-[170px] sm:min-w-[190px]">
          {/* Header with arrow ↗ */}
          <div className="flex items-center justify-between">
            <span className="text-xs sm:text-[13px] font-semibold text-[#14121F] tracking-tight">
              {featuresContent.uiCards.leetcode.title}
            </span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[#14121F]" />
          </div>
          <p className="text-[10px] text-[#71717A] -mt-1 leading-tight">
            {featuresContent.uiCards.leetcode.subtext}
          </p>

          {/* Problem rows separated by a thin line */}
          <div className="mt-1 pt-1.5 border-t border-[#14121F]/10 flex flex-col gap-1.5">
            {featuresContent.uiCards.leetcode.problems.map((prob) => (
              <div key={prob.id} className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded-full bg-[#EDE7FF] text-[#6C5CFF] flex items-center justify-center">
                    <Check className="w-2.5 h-2.5 stroke-[2.5]" />
                  </span>
                  <span className="font-medium text-[#14121F]">{prob.name}</span>
                </div>
                <span
                  className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-md ${
                    prob.tag === 'Easy'
                      ? 'bg-[#EDE7FF] text-[#6C5CFF]'
                      : 'bg-[#E0F2FE] text-[#0284C7]'
                  }`}
                >
                  {prob.tag}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. COMPLEXITY UI CARD */}
      {type === 'complexity' && (
        <div className="flex flex-col gap-1.5 min-w-[160px] sm:min-w-[180px]">
          <div className="flex items-center justify-between text-[10px] text-[#71717A] font-medium">
            <span>{featuresContent.uiCards.complexity.label}</span>
            <span className="text-[#6C5CFF] font-semibold">{featuresContent.uiCards.complexity.badge}</span>
          </div>
          <div className="text-xl sm:text-2xl font-semibold text-[#14121F] tracking-tight font-mono">
            {featuresContent.uiCards.complexity.value}
          </div>

          {/* Bar chart of ~9 rounded vertical bars animating gently */}
          <div className="flex items-end gap-1.5 h-9 pt-1.5 border-t border-[#14121F]/10">
            {[35, 60, 45, 80, 55, 90, 70, 95, 65].map((heightPct, idx) => (
              <div
                key={idx}
                className="w-2 rounded-full border border-[#6C5CFF]/30 bg-[#EDE7FF] overflow-hidden flex flex-col justify-end"
                style={{ height: '100%' }}
              >
                <div
                  className="w-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    height: `${heightPct}%`,
                    background: 'linear-gradient(to top, #6C5CFF, #B33CF0)',
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
