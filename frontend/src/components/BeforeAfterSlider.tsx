"use client";

import Image from "next/image";
import { useCallback, useRef, useState } from "react";

interface BeforeAfterSliderProps {
  before: string;
  after: string;
  alt: string;
}

export function BeforeAfterSlider({ before, after, alt }: BeforeAfterSliderProps) {
  const [position, setPosition] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPosition(Math.min(100, Math.max(0, pct)));
  }, []);

  const onPointerDown = (e: React.PointerEvent) => {
    draggingRef.current = true;
    (e.target as Element).setPointerCapture(e.pointerId);
    updateFromClientX(e.clientX);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!draggingRef.current) return;
    updateFromClientX(e.clientX);
  };

  const onPointerUp = () => {
    draggingRef.current = false;
  };

  return (
    <div
      ref={containerRef}
      className="relative aspect-[4/5] w-full touch-none overflow-hidden rounded-lg border border-border select-none"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <Image src={before} alt={`${alt} — before`} fill priority className="pointer-events-none object-cover" />
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden"
        style={{ clipPath: `inset(0 0 0 ${position}%)` }}
      >
        <Image src={after} alt={`${alt} — after`} fill priority className="object-cover" />
      </div>

      <div
        className="pointer-events-none absolute inset-y-0 w-px bg-white/80"
        style={{ left: `${position}%` }}
      >
        <div className="absolute top-1/2 left-1/2 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/40 bg-black/60 font-mono text-xs text-white backdrop-blur">
          <span className="-mr-0.5">‹</span>
          <span className="-ml-0.5">›</span>
        </div>
      </div>

      <span className="pointer-events-none absolute top-3 left-3 font-mono text-[10px] tracking-widest text-white/70 uppercase">
        Before
      </span>
      <span className="pointer-events-none absolute top-3 right-3 font-mono text-[10px] tracking-widest text-white/70 uppercase">
        After
      </span>
    </div>
  );
}
