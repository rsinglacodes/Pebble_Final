import { useEffect, useState, useRef } from 'react';
import { getPointer, subscribeIdle, PointerData } from '../lib/pointerStore.ts';

export interface PointerState {
  x: number;
  y: number;
  clientX: number;
  clientY: number;
  isIdle: boolean;
  isFinePointer: boolean;
  targetFocus: { x: number; y: number } | null;
}

export function usePointer() {
  const initial = getPointer();
  const [isIdle, setIsIdle] = useState(initial.isIdle);
  const targetFocusRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    return subscribeIdle((idle) => {
      setIsIdle(idle);
    });
  }, []);

  const p = getPointer();

  const setTargetFocus = (pos: { x: number; y: number } | null) => {
    targetFocusRef.current = pos;
  };

  return {
    x: p.x,
    y: p.y,
    clientX: p.clientX,
    clientY: p.clientY,
    isIdle,
    isFinePointer: p.isFinePointer,
    targetFocus: targetFocusRef.current,
    setTargetFocus,
  };
}
