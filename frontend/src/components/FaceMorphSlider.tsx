"use client";

import Image from "next/image";
import { useState } from "react";

interface FaceMorphSliderProps {
  folder: string;
  min: number;
  max: number;
  step: number;
  unit?: string;
  label: string;
}

function Portrait({
  folder,
  person,
  value,
  min,
  step,
}: {
  folder: string;
  person: "man" | "woman";
  value: number;
  min: number;
  step: number;
}) {
  const idx = (value - min) / step;
  const lowerIdx = Math.floor(idx);
  const upperIdx = Math.ceil(idx);
  const frac = idx - lowerIdx;
  const lower = min + lowerIdx * step;
  const upper = min + upperIdx * step;

  return (
    <div className="relative aspect-[238/352] w-full overflow-hidden rounded-lg border border-border">
      <Image src={`/${folder}/${person}-${lower}.jpg`} alt={`${person} at ${lower}`} fill className="object-cover" />
      {upper !== lower && (
        <Image
          src={`/${folder}/${person}-${upper}.jpg`}
          alt={`${person} at ${upper}`}
          fill
          className="object-cover transition-opacity duration-75"
          style={{ opacity: frac }}
        />
      )}
    </div>
  );
}

export function FaceMorphSlider({ folder, min, max, step, unit = "", label }: FaceMorphSliderProps) {
  const [value, setValue] = useState(min);

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="grid grid-cols-2 gap-4">
        <Portrait folder={folder} person="man" value={value} min={min} step={step} />
        <Portrait folder={folder} person="woman" value={value} min={min} step={step} />
      </div>

      <div className="mt-6 flex items-center gap-4">
        <span className="font-mono text-xs text-foreground/50">
          {min}
          {unit}
        </span>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => setValue(Number(e.target.value))}
          className="h-1 w-full flex-1 cursor-pointer appearance-none rounded-full bg-foreground/15 accent-foreground"
          aria-label={label}
        />
        <span className="font-mono text-xs text-foreground/50">
          {max}
          {unit}
        </span>
      </div>
      <p className="mt-2 text-center font-mono text-sm tracking-widest">
        {label} {value}
        {unit}
      </p>
    </div>
  );
}
