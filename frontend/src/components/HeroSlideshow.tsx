"use client";

import { useEffect, useState } from "react";
import { BeforeAfterSlider } from "@/components/BeforeAfterSlider";

const PAIR_COUNT = 5;
const AUTO_ADVANCE_MS = 5000;

const pairs = Array.from({ length: PAIR_COUNT }, (_, i) => {
  const n = i + 1;
  return {
    before: `/hero/${n} (before).jpg`,
    after: `/hero/${n} (after).jpg`,
  };
});

export function HeroSlideshow() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % pairs.length);
    }, AUTO_ADVANCE_MS);
    return () => clearInterval(id);
  }, []);

  const pair = pairs[index];

  return (
    <div className="w-full max-w-sm">
      <BeforeAfterSlider key={index} before={pair.before} after={pair.after} alt={`Face morph example ${index + 1}`} />
      <div className="mt-3 flex justify-center gap-1.5">
        {pairs.map((_, i) => (
          <button
            key={i}
            type="button"
            aria-label={`Show example ${i + 1}`}
            onClick={() => setIndex(i)}
            className={`h-1.5 rounded-full transition-all ${
              i === index ? "w-5 bg-foreground" : "w-1.5 bg-foreground/25"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
