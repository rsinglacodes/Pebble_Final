import React, { useRef, useState } from 'react';
import { motion, useInView } from 'motion/react';
import { footerContent, FooterLinkItem } from '../content.ts';

interface FooterProps {
  onInteractiveHoverStart?: (label?: string) => void;
  onInteractiveHoverEnd?: () => void;
  onOpenAuth?: () => void;
  isLoggedIn?: boolean;
  onOpenChatbot?: () => void;
}

export const Footer: React.FC<FooterProps> = ({
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
  onOpenAuth,
  isLoggedIn = false,
  onOpenChatbot,
}) => {
  const handleCtaClick = isLoggedIn ? (onOpenChatbot ?? onOpenAuth) : onOpenAuth;
  const ctaText = isLoggedIn ? 'Open chatbot' : footerContent.brand.cta;
  const footerRef = useRef<HTMLElement | null>(null);
  const isInView = useInView(footerRef, { amount: 0.15, once: true });

  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  // Check reduced motion
  const isReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim() && email.includes('@')) {
      setIsSubmitted(true);
      setEmail('');
    }
  };

  const handleLinkClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string, isAnchor?: boolean) => {
    if (isAnchor) {
      e.preventDefault();
      if (href === '#world' || href === '#') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        const target = document.querySelector(href);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      }
    }
  };

  const letters = footerContent.wordmark.split('');

  return (
    <footer
      id="hi"
      ref={footerRef}
      className="relative w-full z-20 px-6 sm:px-10 md:px-14 pb-6 select-none bg-transparent"
    >
      {/* ONE Frosted Glass Panel for All Footer Content */}
      <motion.div
        initial={isReducedMotion ? { opacity: 0 } : { opacity: 0, y: 18 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.15 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        onMouseEnter={() => onInteractiveHoverStart?.('footer')}
        onMouseLeave={onInteractiveHoverEnd}
        className="w-full mx-auto mt-[10vh] relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.18) 100%)',
          backdropFilter: 'blur(34px) saturate(180%)',
          WebkitBackdropFilter: 'blur(34px) saturate(180%)',
          border: '1.5px solid rgba(255, 255, 255, 0.75)',
          borderRadius: '32px',
          boxShadow:
            'inset 0 1.5px 2px 0 rgba(255, 255, 255, 0.95), inset 0 -1.5px 2px 0 rgba(255, 255, 255, 0.25), 0 24px 60px -12px rgba(99, 102, 241, 0.10), 0 12px 28px -8px rgba(0, 0, 0, 0.04)',
          padding: 'clamp(28px, 4vw, 56px)',
        }}
      >
        {/* Ambient luminous glow spheres behind the footer glass */}
        <div className="absolute -top-12 left-1/4 w-[380px] h-[380px] rounded-full bg-gradient-to-br from-[#8B5CF6]/20 to-[#6366F1]/15 blur-[90px] pointer-events-none z-0" />
        <div className="absolute -bottom-12 right-1/4 w-[400px] h-[400px] rounded-full bg-gradient-to-tr from-[#38BDF8]/20 to-[#06B6D4]/15 blur-[95px] pointer-events-none z-0" />
        {/* Top 2-Column Block */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-start">
          {/* Left Column (Brand + Tagline + Start Learning CTA + Email Form) */}
          <div className="lg:col-span-6 flex flex-col items-start pr-0 lg:pr-8">
            {/* Logo & Brand Name */}
            <div
              className="flex items-center gap-3 cursor-pointer group"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              onMouseEnter={() => onInteractiveHoverStart?.('logo')}
              onMouseLeave={onInteractiveHoverEnd}
            >
              {/* Mini Robot Head Vector */}
              <div className="w-8 h-8 rounded-[10px] bg-white/80 backdrop-blur-md border border-white/90 shadow-[0_2px_8px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,1)] flex items-center justify-center relative overflow-hidden group-hover:scale-105 transition-transform duration-300">
                <div className="w-5 h-2.5 rounded-[5px] bg-[#111113] flex items-center justify-center gap-1 px-1">
                  <span className="w-1.5 h-0.5 rounded-full bg-[#3CC8FF] shadow-[0_0_4px_#3CC8FF]" />
                  <span className="w-1.5 h-0.5 rounded-full bg-[#B33CF0] shadow-[0_0_4px_#B33CF0]" />
                </div>
              </div>
              <span className="font-semibold text-2xl tracking-tight text-[#111113]">
                {footerContent.brand.name}
              </span>
            </div>

            {/* Tagline: near-black #111 */}
            <p className="mt-4 text-[#111113] text-base sm:text-lg font-normal leading-relaxed whitespace-pre-line max-w-sm">
              {footerContent.brand.tagline}
            </p>

            {/* CTA Button: black with white text */}
            <button
              type="button"
              onClick={handleCtaClick}
              data-cursor="button"
              onMouseEnter={() => onInteractiveHoverStart?.(isLoggedIn ? 'chatbot-cta' : 'cta')}
              onMouseLeave={onInteractiveHoverEnd}
              className="mt-6 px-6 py-2.5 rounded-full bg-[#111113] text-white text-sm font-medium tracking-tight shadow-[0_4px_14px_rgba(0,0,0,0.12)] cursor-pointer inline-flex items-center gap-2 active:scale-98 transition-transform"
            >
              <span>{ctaText}</span>
            </button>

            {/* Email Subscription Pill Form */}
            <div className="mt-8 w-full max-w-md">
              {isSubmitted ? (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/90 backdrop-blur-md border border-white/80 text-xs font-medium text-[#111113] shadow-xs"
                >
                  <svg className="w-4 h-4 text-[#6C5CFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>{footerContent.newsletter.successMessage}</span>
                </motion.div>
              ) : (
                <form
                  onSubmit={handleSubmit}
                  className="relative flex items-center bg-white/75 backdrop-blur-md border border-white/90 rounded-full p-1.5 shadow-[0_4px_16px_rgba(0,0,0,0.04),inset_0_1px_0_rgba(255,255,255,0.9)] focus-within:border-[#111113]/30 transition-all"
                >
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={footerContent.newsletter.placeholder}
                    required
                    className="bg-transparent text-sm text-[#111113] placeholder:text-[#6B6B73] outline-none px-3.5 flex-1 w-full rounded-l-full"
                  />
                  <button
                    type="submit"
                    onMouseEnter={() => onInteractiveHoverStart?.('button')}
                    onMouseLeave={onInteractiveHoverEnd}
                    className="px-5 py-2 rounded-full bg-[#111113] text-white text-xs font-medium cursor-pointer shrink-0 active:scale-95 transition-transform"
                  >
                    {footerContent.newsletter.buttonText}
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* Right Column (3 Staggered Link Columns) */}
          <div className="lg:col-span-6 grid grid-cols-2 sm:grid-cols-3 gap-8">
            {footerContent.columns.map((col, colIdx) => (
              <motion.div
                key={col.title}
                initial={isReducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.15 }}
                transition={{
                  duration: 0.6,
                  delay: isReducedMotion ? 0 : colIdx * 0.1,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="flex flex-col items-start"
              >
                {/* Column Headings: #3A3A42 */}
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3A3A42] mb-4">
                  {col.title}
                </h4>
                <ul className="space-y-3">
                  {col.links.map((link: FooterLinkItem) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        onClick={(e) => handleLinkClick(e, link.href, link.isAnchor)}
                        target={link.href.startsWith('http') ? '_blank' : undefined}
                        rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                        onMouseEnter={() => onInteractiveHoverStart?.('link')}
                        onMouseLeave={onInteractiveHoverEnd}
                        className="text-sm text-[#55555D] hover:text-[#111113] inline-flex items-center gap-2 group cursor-pointer transition-colors"
                      >
                        {link.icon === 'github' && (
                          <svg className="w-4 h-4 text-[#55555D] group-hover:text-[#111113] shrink-0 transition-colors" fill="currentColor" viewBox="0 0 24 24">
                            <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                          </svg>
                        )}
                        {link.icon === 'x' && (
                          <svg className="w-3.5 h-3.5 text-[#55555D] group-hover:text-[#111113] shrink-0 transition-colors" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                          </svg>
                        )}
                        {link.icon === 'linkedin' && (
                          <svg className="w-4 h-4 text-[#55555D] group-hover:text-[#111113] shrink-0 transition-colors" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                          </svg>
                        )}
                        {link.icon === 'mail' && (
                          <svg className="w-4 h-4 text-[#55555D] group-hover:text-[#111113] shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                          </svg>
                        )}
                        {/* Label with Sliding Underline on Hover */}
                        <span className="relative inline-block">
                          {link.label}
                          <span className="absolute left-0 -bottom-0.5 w-0 h-[1.5px] bg-[#111113] transition-all duration-300 group-hover:w-full" />
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Bottom Bar inside the glass panel, separated by hairline rgba(17,17,17,0.08) */}
        <div className="w-full h-[1px] bg-[rgba(17,17,17,0.08)] mt-12 mb-6" />
        <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-[#55555D] gap-4">
          <span>{footerContent.bottom.copyright}</span>
          <div className="flex items-center gap-6">
            {footerContent.bottom.legal.map((item) => (
              <a
                key={item.label}
                href={item.href}
                onMouseEnter={() => onInteractiveHoverStart?.('link')}
                onMouseLeave={onInteractiveHoverEnd}
                className="text-[#55555D] hover:text-[#111113] transition-colors relative inline-block group cursor-pointer"
              >
                <span>{item.label}</span>
                <span className="absolute left-0 -bottom-0.5 w-0 h-[1px] bg-[#111113] transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Giant Wordmark "pebble" OUTSIDE and BELOW the glass panel, ~22% opacity, cropped bottom ~30% */}
      <div className="relative w-full overflow-hidden flex items-start justify-center h-[clamp(110px,18vw,260px)] pointer-events-none mt-6 sm:mt-8">
        <div className="flex items-center justify-center font-black tracking-tighter leading-none text-[21vw] sm:text-[22vw] select-none opacity-[0.22] bg-gradient-to-r from-[#B33CF0] via-[#6C5CFF] to-[#3CC8FF] bg-clip-text text-transparent">
          {letters.map((char, i) => (
            <span
              key={`${char}-${i}`}
              className="inline-block overflow-hidden pb-4"
            >
              <motion.span
                initial={isReducedMotion ? { opacity: 0 } : { y: '100%', opacity: 0 }}
                animate={
                  isInView
                    ? { y: '0%', opacity: 1 }
                    : isReducedMotion
                      ? { opacity: 0 }
                      : { y: '100%', opacity: 0 }
                }
                transition={{
                  duration: isReducedMotion ? 0.4 : 1.3,
                  delay: isReducedMotion ? 0 : 0.2 + i * 0.08,
                  ease: [0.22, 1, 0.36, 1],
                }}
                className="inline-block"
              >
                {char}
              </motion.span>
            </span>
          ))}
        </div>
      </div>
    </footer>
  );
};
