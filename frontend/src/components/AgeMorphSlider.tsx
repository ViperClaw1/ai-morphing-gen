"use client";

import Image from "next/image";
import { useState } from "react";

const AGES = [20, 30, 40, 50, 60];

function AgePortrait({ person, age }: { person: "man" | "woman"; age: number }) {
  const idx = (age - 20) / 10;
  const lower = AGES[Math.floor(idx)];
  const upper = AGES[Math.ceil(idx)];
  const frac = idx - Math.floor(idx);

  return (
    <div className="relative aspect-[235/352] w-full overflow-hidden rounded-lg border border-border">
      <Image src={`/age-morph/${person}-${lower}.jpg`} alt={`${person} at ${lower}`} fill className="object-cover" />
      {upper !== lower && (
        <Image
          src={`/age-morph/${person}-${upper}.jpg`}
          alt={`${person} at ${upper}`}
          fill
          className="object-cover transition-opacity duration-75"
          style={{ opacity: frac }}
        />
      )}
    </div>
  );
}

export function AgeMorphSlider() {
  const [age, setAge] = useState(20);

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="grid grid-cols-2 gap-4">
        <AgePortrait person="man" age={age} />
        <AgePortrait person="woman" age={age} />
      </div>

      <div className="mt-6 flex items-center gap-4">
        <span className="font-mono text-xs text-foreground/50">20</span>
        <input
          type="range"
          min={20}
          max={60}
          step={1}
          value={age}
          onChange={(e) => setAge(Number(e.target.value))}
          className="h-1 w-full flex-1 cursor-pointer appearance-none rounded-full bg-foreground/15 accent-foreground"
          aria-label="Age"
        />
        <span className="font-mono text-xs text-foreground/50">60</span>
      </div>
      <p className="mt-2 text-center font-mono text-sm tracking-widest">AGE {age}</p>
    </div>
  );
}
