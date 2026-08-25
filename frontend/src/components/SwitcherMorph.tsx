"use client";

import Image from "next/image";
import { useState } from "react";

interface SwitcherOption {
  key: string;
  label: string;
}

interface SwitcherMorphProps {
  folder: string;
  options: SwitcherOption[];
  altSuffix: string;
}

function SwitcherPortrait({
  folder,
  person,
  options,
  altSuffix,
  index,
}: {
  folder: string;
  person: "man" | "woman";
  options: SwitcherOption[];
  altSuffix: string;
  index: number;
}) {
  return (
    <div className="relative aspect-[236/365] w-full overflow-hidden rounded-lg border border-border">
      {options.map((opt, i) => (
        <Image
          key={opt.key}
          src={`/${folder}/${person}-${opt.key}.jpg`}
          alt={`${person} with ${opt.label.toLowerCase()} ${altSuffix}`}
          fill
          priority={i === 0}
          className="object-cover transition-opacity duration-300 ease-in-out"
          style={{ opacity: i === index ? 1 : 0 }}
        />
      ))}
    </div>
  );
}

export function SwitcherMorph({ folder, options, altSuffix }: SwitcherMorphProps) {
  const [index, setIndex] = useState(0);

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="grid grid-cols-2 gap-4">
        <SwitcherPortrait folder={folder} person="man" options={options} altSuffix={altSuffix} index={index} />
        <SwitcherPortrait folder={folder} person="woman" options={options} altSuffix={altSuffix} index={index} />
      </div>

      <div className="relative mt-6 flex overflow-hidden rounded-full border border-border">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-foreground transition-transform duration-300 ease-in-out"
          style={{ width: `${100 / options.length}%`, transform: `translateX(${index * 100}%)` }}
        />
        {options.map((opt, i) => (
          <button
            key={opt.key}
            type="button"
            onClick={() => setIndex(i)}
            className={`relative z-10 flex-1 cursor-pointer px-1 py-2 text-center font-mono text-[10px] uppercase tracking-wide transition-colors ${
              i === index ? "text-background" : "text-foreground/60 hover:text-foreground"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
