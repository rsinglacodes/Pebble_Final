/**
 * Ultra-low latency global pointer store.
 * Eliminates React re-renders on mouse movement.
 * Directly tracks coordinates and delegated cursor hover targets.
 */

export interface PointerData {
  clientX: number;
  clientY: number;
  x: number; // -1 to 1 (left to right)
  y: number; // -1 to 1 (top to bottom)
  isIdle: boolean;
  isFinePointer: boolean;
  hoverType: string | null;
}

const pointerData: PointerData = {
  clientX: typeof window !== 'undefined' ? window.innerWidth / 2 : 500,
  clientY: typeof window !== 'undefined' ? window.innerHeight / 2 : 400,
  x: 0,
  y: 0,
  isIdle: false,
  isFinePointer: true,
  hoverType: null,
};

type HoverListener = (hoverType: string | null) => void;
type IdleListener = (isIdle: boolean) => void;

const hoverListeners = new Set<HoverListener>();
const idleListeners = new Set<IdleListener>();

let isInitialized = false;
let idleTimer: number | null = null;

export function initPointerStore(): void {
  if (isInitialized || typeof window === 'undefined') return;
  isInitialized = true;

  pointerData.isFinePointer =
    window.matchMedia('(pointer: fine)').matches ||
    window.matchMedia('(any-pointer: fine)').matches;

  const resetIdle = () => {
    if (idleTimer !== null) {
      window.clearTimeout(idleTimer);
    }
    if (pointerData.isIdle) {
      pointerData.isIdle = false;
      idleListeners.forEach((fn) => fn(false));
    }
    idleTimer = window.setTimeout(() => {
      pointerData.isIdle = true;
      idleListeners.forEach((fn) => fn(true));
    }, 3000);
  };

  const onPointerMove = (e: MouseEvent | TouchEvent | PointerEvent) => {
    let cx = pointerData.clientX;
    let cy = pointerData.clientY;

    if ('touches' in e && e.touches.length > 0) {
      cx = e.touches[0].clientX;
      cy = e.touches[0].clientY;
    } else if ('clientX' in e) {
      cx = (e as MouseEvent).clientX;
      cy = (e as MouseEvent).clientY;
    }

    pointerData.clientX = cx;
    pointerData.clientY = cy;

    const w = window.innerWidth || 1;
    const h = window.innerHeight || 1;
    pointerData.x = (cx / w) * 2 - 1;
    pointerData.y = (cy / h) * 2 - 1;

    resetIdle();
  };

  const onPointerOver = (e: Event) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;

    // 1. Explicit data-cursor attribute
    const explicit = target.closest<HTMLElement>('[data-cursor]');
    if (explicit) {
      const type = explicit.getAttribute('data-cursor') || 'button';
      setHoverType(type);
      return;
    }

    // 2. Text input or textarea
    if (
      target.closest(
        'input:not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]), textarea, [contenteditable="true"]'
      )
    ) {
      setHoverType('input');
      return;
    }

    // 3. Interactive button, anchor, tab
    if (target.closest('button, a[href], [role="button"], [role="tab"], .cursor-pointer')) {
      setHoverType('button');
      return;
    }

    // Default neutral
    setHoverType(null);
  };

  const onPointerLeave = () => {
    setHoverType(null);
  };

  window.addEventListener('pointermove', onPointerMove, { passive: true });
  window.addEventListener('mousemove', onPointerMove, { passive: true });
  window.addEventListener('touchstart', onPointerMove, { passive: true });
  window.addEventListener('touchmove', onPointerMove, { passive: true });
  document.addEventListener('mouseover', onPointerOver, { passive: true });
  document.addEventListener('mouseleave', onPointerLeave);
}

function setHoverType(newType: string | null) {
  if (pointerData.hoverType !== newType) {
    pointerData.hoverType = newType;
    hoverListeners.forEach((fn) => fn(newType));
  }
}

export function getPointer(): PointerData {
  if (!isInitialized) {
    initPointerStore();
  }
  return pointerData;
}

export function subscribeHover(callback: HoverListener): () => void {
  if (!isInitialized) initPointerStore();
  hoverListeners.add(callback);
  callback(pointerData.hoverType);
  return () => hoverListeners.delete(callback);
}

export function subscribeIdle(callback: IdleListener): () => void {
  if (!isInitialized) initPointerStore();
  idleListeners.add(callback);
  callback(pointerData.isIdle);
  return () => idleListeners.delete(callback);
}

// Auto-initialize in browser
if (typeof window !== 'undefined') {
  initPointerStore();
}
