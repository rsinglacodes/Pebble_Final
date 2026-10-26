import React, { useEffect, useRef, useState } from 'react';
import { defaultColors } from '../content.ts';
import { getPointer, subscribeHover } from '../lib/pointerStore.ts';

interface CursorProps {
  hoverType?: string | null;
}

export const Cursor: React.FC<CursorProps> = ({ hoverType: explicitHoverType }) => {
  const ringRef = useRef<HTMLDivElement | null>(null);
  const dotRef = useRef<HTMLDivElement | null>(null);
  const [delegatedHover, setDelegatedHover] = useState<string | null>(null);

  // Subscribe to hover changes without triggering mousemove renders
  useEffect(() => {
    return subscribeHover((type) => {
      setDelegatedHover(type);
    });
  }, []);

  const activeHover =
    explicitHoverType !== undefined && explicitHoverType !== null
      ? explicitHoverType
      : delegatedHover;

  useEffect(() => {
    // Only show custom cursor on fine/mouse pointer devices
    const isFine =
      window.matchMedia('(pointer: fine)').matches ||
      window.matchMedia('(any-pointer: fine)').matches;

    if (!isFine) return;

    let ringX = -100;
    let ringY = -100;
    let hasMoved = false;
    let animId: number;

    const loop = () => {
      const pointer = getPointer();
      const targetX = pointer.clientX;
      const targetY = pointer.clientY;

      if (!hasMoved && targetX > 0 && targetY > 0) {
        hasMoved = true;
        ringX = targetX;
        ringY = targetY;
      }

      if (hasMoved) {
        // Ultra-low latency: Dot follows instantaneously with 0 delay
        if (dotRef.current) {
          dotRef.current.style.transform = `translate3d(${targetX}px, ${targetY}px, 0) translate(-50%, -50%)`;
          dotRef.current.style.opacity = activeHover === 'input' ? '0.25' : '1';
        }

        // Snappy lerp for ring (0.35 per frame for responsive tracking without jitter)
        ringX += (targetX - ringX) * 0.35;
        ringY += (targetY - ringY) * 0.35;

        if (ringRef.current) {
          ringRef.current.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%)`;
          ringRef.current.style.opacity = activeHover === 'input' ? '0.25' : '1';
        }
      }

      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [activeHover]);

  const isInput = activeHover === 'input';
  const isExpanded = activeHover !== null && !isInput;
  const borderColor = defaultColors.cursorRing;
  const fillColor = isExpanded ? defaultColors.cursorFill : 'transparent';

  return (
    <div
      className="hidden pointer-events-none md:block fixed inset-0 z-[9999] overflow-hidden select-none"
      aria-hidden="true"
    >
      {/* Outer Follower Ring with Snappy Lerp */}
      <div
        ref={ringRef}
        className="fixed top-0 left-0 rounded-full transition-[width,height,background-color,border-color,box-shadow] duration-200 ease-out will-change-transform opacity-0"
        style={{
          width: isExpanded ? '44px' : '26px',
          height: isExpanded ? '44px' : '26px',
          borderWidth: '1.5px',
          borderStyle: 'solid',
          borderColor: borderColor,
          backgroundColor: fillColor,
          boxShadow: isExpanded ? `0 0 16px ${borderColor}` : 'none',
        }}
      />

      {/* Trailing Center Dot with 0ms Lag */}
      <div
        ref={dotRef}
        className="fixed top-0 left-0 w-1.5 h-1.5 rounded-full will-change-transform opacity-0"
        style={{
          backgroundColor: defaultColors.gradientMid,
        }}
      />
    </div>
  );
};
