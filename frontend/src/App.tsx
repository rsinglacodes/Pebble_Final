import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { HexBackground } from './components/HexBackground.tsx';
import { Nav } from './components/Nav.tsx';
import { Hero } from './components/Hero.tsx';
import { Robot } from './components/Robot.tsx';
import { CarouselCard } from './components/CarouselCard.tsx';
import { Cursor } from './components/Cursor.tsx';
import { usePointer } from './hooks/usePointer.ts';
import { Features } from './components/Features/Features.tsx';
import { Footer } from './components/Footer.tsx';
import { useAuthModal } from './hooks/useAuthModal.ts';
import { AuthModal } from './components/Auth/AuthModal.tsx';
import { useAppRoute } from './hooks/useAppRoute.ts';
import { HomePage } from './components/Home/HomePage.tsx';

export default function App() {
  const pointer = usePointer();
  const authModal = useAuthModal();

  const { route, navigate, logout } = useAppRoute(() => {
    authModal.openLogIn();
  });

  const [activeLinkId, setActiveLinkId] = useState('explore');

  const handleNavSelect = (id: string) => {
    setActiveLinkId(id);
    if (id === 'explore' || id === 'world') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (id === 'features' || id === 'tricks') {
      document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
    } else if (id === 'about' || id === 'hi' || id === 'story') {
      document.getElementById('hi')?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Fix 3: Every Adopt Me button ALWAYS opens the auth overlay on the SIGN UP tab
  const handleAdoptClick = () => {
    authModal.openSignUp();
  };

  const handleAuthSuccessNavigate = () => {
    authModal.close();
    navigate('home');
  };

  return (
    <div className="relative w-full min-h-screen bg-[#F7F7F8] p-2 select-none overflow-x-clip">
      {/* Custom Ultra-Low Latency Desktop Follower Cursor */}
      <Cursor />

      {/* Route Switcher: Only ONE page mounted at any time to free GPU/CPU */}
      <AnimatePresence mode="wait">
        {route === 'home' ? (
          <motion.div
            key="home-page-view"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="fixed inset-0 z-30"
          >
            <HomePage
              onLogout={logout}
              onGoToLanding={() => navigate('landing')}
            />
          </motion.div>
        ) : (
          <motion.div
            key="landing-page-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full"
          >
            {/* ONE Continuous Main Neumorphic Panel with 8px Window Margin */}
            <main
              className="relative w-full max-w-[1720px] mx-auto bg-[#ECECEE] rounded-[24px] sm:rounded-[28px] animate-panelFade"
              style={{
                boxShadow:
                  'inset 0 1px 2px rgba(255, 255, 255, 0.8), 0 12px 36px rgba(0, 0, 0, 0.03)',
              }}
            >
              {/* Continuous Breathing Hex Honeycomb Background across full page height */}
              <div className="absolute inset-0 z-0 pointer-events-none rounded-[24px] sm:rounded-[28px] overflow-hidden">
                <HexBackground pointerX={pointer.x} pointerY={pointer.y} />
              </div>

              {/* Page 1 (Hero Section) */}
              <section
                id="world"
                className="relative z-10 w-full h-screen min-h-[640px] max-h-[1100px] flex flex-col justify-between"
              >
                {/* Top Navigation */}
                <div className="w-full animate-navDrop">
                  <Nav
                    activeLinkId={activeLinkId}
                    onSelectLink={handleNavSelect}
                    onInteractiveHoverStart={() => {}}
                    onInteractiveHoverEnd={() => {}}
                    onOpenAuth={handleAdoptClick}
                  />
                </div>

                {/* Center Canvas & Content Viewport */}
                <div className="relative flex-1 w-full px-6 sm:px-10 md:px-14 flex flex-col md:flex-row items-center justify-between pb-6 sm:pb-8">
                  {/* Left Hero Headline & CTA */}
                  <div className="w-full md:w-auto flex justify-start items-center my-auto z-20">
                    <div className="animate-heroStagger">
                      <Hero
                        onInteractiveHoverStart={() => {}}
                        onInteractiveHoverEnd={() => {}}
                        onOpenAuth={handleAdoptClick}
                      />
                    </div>
                  </div>

                  {/* Center 3D Interactive Robot Head (Fix 1: Original Robot restored) */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-15">
                    <div className="pointer-events-auto transform -translate-y-2 sm:-translate-y-4">
                      <Robot
                        clientX={pointer.clientX}
                        clientY={pointer.clientY}
                        isIdle={pointer.isIdle}
                      />
                    </div>
                  </div>

                  {/* Bottom-Right Frosted Carousel Card */}
                  <div className="w-full md:w-auto flex justify-end items-end mt-auto z-20 ml-auto animate-cardSlideUp">
                    <CarouselCard
                      onInteractiveHoverStart={() => {}}
                      onInteractiveHoverEnd={() => {}}
                    />
                  </div>
                </div>
              </section>

              {/* Page 2 (Features Section with Pinned Sticky Horizontal Scroll) */}
              <div id="features" className="relative z-10 w-full">
                <Features
                  onInteractiveHoverStart={() => {}}
                  onInteractiveHoverEnd={() => {}}
                />
              </div>

              {/* Footer Section */}
              <Footer
                onInteractiveHoverStart={() => {}}
                onInteractiveHoverEnd={() => {}}
                onOpenAuth={handleAdoptClick}
              />
            </main>

            {/* Full-Screen Auth Overlay */}
            <AuthModal
              isOpen={authModal.isOpen}
              mode={authModal.mode}
              onClose={authModal.close}
              onSwitchMode={authModal.switchMode}
              onSuccessNavigate={handleAuthSuccessNavigate}
              clientX={pointer.clientX}
              clientY={pointer.clientY}
              isIdle={pointer.isIdle}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Intro Animation Styles */}
      <style>{`
        @keyframes panelFade {
          0% {
            opacity: 0;
          }
          100% {
            opacity: 1;
          }
        }

        @keyframes navDrop {
          0% {
            opacity: 0;
            transform: translateY(-20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes heroStagger {
          0% {
            opacity: 0;
            transform: translateY(24px);
            filter: blur(8px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
            filter: blur(0);
          }
        }

        @keyframes cardSlideUp {
          0% {
            opacity: 0;
            transform: translateY(32px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-panelFade {
          animation: panelFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        .animate-navDrop {
          animation: navDrop 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.5s both;
        }

        .animate-heroStagger {
          animation: heroStagger 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.75s both;
        }

        .animate-cardSlideUp {
          animation: cardSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 1.1s both;
        }

        @media (prefers-reduced-motion: reduce) {
          .animate-panelFade,
          .animate-navDrop,
          .animate-heroStagger,
          .animate-cardSlideUp {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
            filter: none !important;
          }
        }
      `}</style>
    </div>
  );
}
