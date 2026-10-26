import React, { useState, useRef, useEffect } from 'react';
import { LogOut, User, Sparkles } from 'lucide-react';
import { getSavedSession } from '../../lib/auth.ts';

interface UserChipProps {
  onLogout: () => void;
  onOpenSettings?: () => void;
}

export const UserChip: React.FC<UserChipProps> = ({ onLogout, onOpenSettings }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const session = getSavedSession();
  const userName = session?.name || 'Explorer';
  const userEmail = session?.email || 'explorer@pebble.dev';

  const initials = userName
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  // Close menu on click outside
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div ref={menuRef} className="relative select-none">
      {/* Trigger Button with Subtle Gradient Ring */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        data-cursor="button"
        title={userName}
        aria-label="User profile menu"
        className="w-10 h-10 rounded-full p-[2px] transition-transform hover:scale-105 active:scale-95 cursor-pointer relative"
        style={{
          background: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
        }}
      >
        <div className="w-full h-full rounded-full bg-[#16161A] text-white flex items-center justify-center font-semibold text-xs tracking-wider shadow-inner">
          {initials}
        </div>
      </button>

      {/* Popover Menu */}
      {isOpen && (
        <div
          className="absolute bottom-12 left-0 sm:left-auto sm:right-0 mb-2 w-64 bg-[#FAFAFB] rounded-[20px] p-2.5 shadow-[0_20px_50px_rgba(0,0,0,0.14)] border border-black/[0.08] z-50 animate-popIn"
          style={{
            animationDuration: '180ms',
          }}
        >
          {/* Header Info */}
          <div className="px-3 py-2.5 border-b border-black/[0.06]">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-[#111113] truncate">
                {userName}
              </span>
              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#6C5CFF]/10 text-[#6C5CFF]">
                Free
              </span>
            </div>
            <p className="text-xs text-[#8A8A90] truncate mt-0.5">{userEmail}</p>
          </div>

          {/* Action List */}
          <div className="py-1 space-y-0.5">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onOpenSettings?.();
              }}
              data-cursor="button"
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-medium text-[#44444C] hover:text-[#111113] hover:bg-black/[0.04] transition-colors cursor-pointer text-left"
            >
              <User className="w-3.5 h-3.5 text-[#6C5CFF]" />
              <span>Preferences</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
              }}
              data-cursor="button"
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-medium text-[#44444C] hover:text-[#111113] hover:bg-black/[0.04] transition-colors cursor-pointer text-left"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#3CC8FF]" />
              <span>Algorithm Library</span>
            </button>

            <div className="w-full h-[1px] bg-black/[0.06] my-1" />

            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onLogout();
              }}
              data-cursor="button"
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-medium text-[#D9485F] hover:bg-[#D9485F]/10 transition-colors cursor-pointer text-left"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Log out</span>
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes popIn {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(4px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-popIn {
          animation: popIn 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
};
