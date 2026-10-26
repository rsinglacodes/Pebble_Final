import React, { useRef, useState } from 'react';
import { motion, useInView } from 'motion/react';
import { Play, Pause } from 'lucide-react';
import { featuresContent } from '../../content.ts';
import { SplitText } from './SplitText.tsx';
import { UiCard } from './UiCard.tsx';
import { TileVideo } from './TileVideo.tsx';
import { TileTwoPointers } from './TileTwoPointers.tsx';
import { TileAlgorithms } from './TileAlgorithms.tsx';
import { TileYourCode } from './TileYourCode.tsx';
import { TileSortingBars } from './TileSortingBars.tsx';

interface FeaturesProps {
  onInteractiveHoverStart?: (label?: string) => void;
  onInteractiveHoverEnd?: () => void;
}

export const Features: React.FC<FeaturesProps> = ({
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
}) => {
  const sectionRef = useRef<HTMLDivElement | null>(null);
  const isInView = useInView(sectionRef, { amount: 0.15, once: true });
  const [isPaused, setIsPaused] = useState(false);

  // 11 distinct feature elements with organic vertical staggers
  const featureItems = [
    {
      id: 'video',
      element: (
        <div className="w-[240px] sm:w-[280px] h-[240px] sm:h-[270px] -translate-y-4">
          <div className="w-full h-full animate-floatA">
            <TileVideo className="w-full h-full" />
          </div>
        </div>
      ),
    },
    {
      id: 'ui-visualize',
      element: (
        <div className="w-[210px] sm:w-[230px] translate-y-7">
          <div className="w-full h-full animate-floatB">
            <UiCard
              type="visualize"
              onHoverStart={() => onInteractiveHoverStart?.('ui-card')}
              onHoverEnd={onInteractiveHoverEnd}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'two-pointers',
      element: (
        <div className="w-[230px] sm:w-[260px] h-[230px] sm:h-[260px] -translate-y-2">
          <div className="w-full h-full animate-floatA">
            <TileTwoPointers className="w-full h-full" />
          </div>
        </div>
      ),
    },
    {
      id: 'fragment-1',
      element: (
        <div className="self-center px-3.5 py-1.5 rounded-full bg-white/80 border border-black/5 shadow-2xs font-mono text-xs text-[#55555D] backdrop-blur-xs translate-y-12 shrink-0 animate-floatB">
          {featuresContent.fragments[0]}
        </div>
      ),
    },
    {
      id: 'algorithms',
      element: (
        <div className="w-[280px] sm:w-[320px] h-[330px] sm:h-[370px] -translate-y-6">
          <div className="w-full h-full animate-floatA">
            <TileAlgorithms className="w-full h-full" />
          </div>
        </div>
      ),
    },
    {
      id: 'ui-leetcode',
      element: (
        <div className="w-[220px] sm:w-[240px] translate-y-8">
          <div className="w-full h-full animate-floatB">
            <UiCard
              type="leetcode"
              onHoverStart={() => onInteractiveHoverStart?.('ui-card')}
              onHoverEnd={onInteractiveHoverEnd}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'fragment-2',
      element: (
        <div className="self-center px-3.5 py-1.5 rounded-full bg-white/80 border border-black/5 shadow-2xs font-mono text-xs text-[#55555D] backdrop-blur-xs -translate-y-9 shrink-0 animate-floatA">
          {featuresContent.fragments[1]}
        </div>
      ),
    },
    {
      id: 'your-code',
      element: (
        <div className="w-[250px] sm:w-[280px] h-[240px] sm:h-[270px] -translate-y-3">
          <div className="w-full h-full animate-floatB">
            <TileYourCode className="w-full h-full" />
          </div>
        </div>
      ),
    },
    {
      id: 'ui-complexity',
      element: (
        <div className="w-[200px] sm:w-[220px] translate-y-6">
          <div className="w-full h-full animate-floatA">
            <UiCard
              type="complexity"
              onHoverStart={() => onInteractiveHoverStart?.('ui-card')}
              onHoverEnd={onInteractiveHoverEnd}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'fragment-3',
      element: (
        <div className="self-center px-3.5 py-1.5 rounded-full bg-white/80 border border-black/5 shadow-2xs font-mono text-xs text-[#55555D] backdrop-blur-xs translate-y-11 shrink-0 animate-floatB">
          {featuresContent.fragments[2]}
        </div>
      ),
    },
    {
      id: 'sorting-bars',
      element: (
        <div className="w-[230px] sm:w-[260px] h-[230px] sm:h-[260px] -translate-y-1">
          <div className="w-full h-full animate-floatA">
            <TileSortingBars className="w-full h-full" />
          </div>
        </div>
      ),
    },
  ];

  return (
    <section
      ref={sectionRef}
      className="w-full bg-transparent select-none p-2 sm:p-3 md:p-4"
    >
      {/* Main Glass Stage Container */}
      <div
        className="relative w-full min-h-[580px] sm:min-h-[640px] md:min-h-[700px] rounded-[28px] sm:rounded-[36px] flex flex-col justify-between overflow-hidden transition-all duration-300"
        style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.18) 100%)',
          backdropFilter: 'blur(34px) saturate(180%)',
          WebkitBackdropFilter: 'blur(34px) saturate(180%)',
          border: '1.5px solid rgba(255, 255, 255, 0.75)',
          boxShadow:
            'inset 0 1.5px 2px 0 rgba(255, 255, 255, 0.95), inset 0 -1.5px 2px 0 rgba(255, 255, 255, 0.3), 0 24px 60px -12px rgba(99, 102, 241, 0.10), 0 12px 28px -8px rgba(0, 0, 0, 0.04)',
        }}
      >
        {/* Ambient luminous glow spheres behind glass */}
        <div className="absolute -top-12 left-1/4 w-[420px] h-[420px] rounded-full bg-gradient-to-br from-[#8B5CF6]/25 to-[#6366F1]/18 blur-[95px] pointer-events-none z-0" />
        <div className="absolute -bottom-16 right-1/4 w-[460px] h-[460px] rounded-full bg-gradient-to-tr from-[#38BDF8]/25 to-[#06B6D4]/18 blur-[105px] pointer-events-none z-0" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] h-[340px] rounded-full bg-gradient-to-b from-[#C084FC]/18 to-[#818CF8]/14 blur-[85px] pointer-events-none z-0" />

        {/* Top Section Header */}
        <div className="w-full px-6 sm:px-10 md:px-14 pt-6 sm:pt-8 flex flex-col md:flex-row items-start md:items-baseline z-30">
          {/* Top-left small label "01-04" */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: -8 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-xs sm:text-[13px] font-medium text-[#111113] tracking-wider mb-2 md:mb-0 w-[14%]"
          >
            {featuresContent.sectionIndex}
          </motion.div>

          {/* Headline, left-aligned */}
          <div className="md:ml-[3%] max-w-2xl">
            <SplitText
              line1={featuresContent.headline.line1}
              line2={featuresContent.headline.line2}
              isVisible={isInView}
              className="text-3xl sm:text-4xl md:text-[clamp(2.4rem,4.6vw,4rem)]"
            />
          </div>
        </div>

        {/* Continuous Smooth Horizontal Motion Track (Moving continuously from right to left) */}
        <div
          className="relative w-full my-auto py-8 overflow-hidden z-20 group"
          onMouseEnter={() => {
            setIsPaused(true);
            onInteractiveHoverStart?.('marquee');
          }}
          onMouseLeave={() => {
            setIsPaused(false);
            onInteractiveHoverEnd?.();
          }}
          style={{
            maskImage: 'linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%)',
          }}
        >
          <div
            className="features-marquee flex items-center gap-6 sm:gap-8 will-change-transform"
            style={{
              animationPlayState: isPaused ? 'paused' : 'running',
            }}
          >
            {/* First Set of Items */}
            <div className="flex items-center gap-6 sm:gap-8 shrink-0">
              {featureItems.map((item, idx) => (
                <div key={`set1-${item.id}-${idx}`} className="shrink-0 flex items-center">
                  {item.element}
                </div>
              ))}
            </div>

            {/* Duplicate Set of Items for Seamless Infinite Continuous Loop */}
            <div className="flex items-center gap-6 sm:gap-8 shrink-0" aria-hidden="true">
              {featureItems.map((item, idx) => (
                <div key={`set2-${item.id}-${idx}`} className="shrink-0 flex items-center">
                  {item.element}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Bar: Interactive Controls & Information Badges */}
        <div className="flex items-center justify-between px-6 sm:px-10 md:px-14 pb-6 text-xs text-[#55555D] font-mono z-20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPaused((prev) => !prev)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/70 hover:bg-white text-[#111113] backdrop-blur-xs border border-white/80 shadow-2xs transition-all duration-200"
              title={isPaused ? 'Resume auto-scroll' : 'Pause auto-scroll'}
            >
              {isPaused ? (
                <>
                  <Play className="w-3 h-3 fill-current" />
                  <span className="text-[11px] font-medium">Resume</span>
                </>
              ) : (
                <>
                  <Pause className="w-3 h-3 fill-current" />
                  <span className="text-[11px] font-medium">Pause</span>
                </>
              )}
            </button>
            <span className="hidden sm:inline px-3 py-1 rounded-full bg-white/50 backdrop-blur-xs border border-white/60 shadow-2xs text-[11px]">
              Hover any card to inspect & interact
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="px-3 py-1 rounded-full bg-white/50 backdrop-blur-xs border border-white/60 shadow-2xs text-[11px]">
              Continuous Right-to-Left Live Feed
            </span>
          </div>
        </div>
      </div>

      {/* Hardware-accelerated continuous infinite marquee animation */}
      <style>{`
        @keyframes marqueeMoveLeft {
          0% {
            transform: translate3d(0, 0, 0);
          }
          100% {
            transform: translate3d(-50%, 0, 0);
          }
        }

        .features-marquee {
          width: max-content;
          animation: marqueeMoveLeft 42s linear infinite;
        }

        .features-marquee:hover {
          animation-play-state: paused;
        }

        @keyframes floatA {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-6px);
          }
        }

        @keyframes floatB {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(6px);
          }
        }

        .animate-floatA {
          animation: floatA 4.8s ease-in-out infinite;
        }

        .animate-floatB {
          animation: floatB 5.4s ease-in-out infinite;
        }

        @media (prefers-reduced-motion: reduce) {
          .features-marquee,
          .animate-floatA,
          .animate-floatB {
            animation: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </section>
  );
};
