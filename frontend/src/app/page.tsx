import Link from "next/link";
import { Button } from "@/components/ui/button";
import { HeroSlideshow } from "@/components/HeroSlideshow";
import { FaceMorphSlider } from "@/components/FaceMorphSlider";
import { SwitcherMorph } from "@/components/SwitcherMorph";

const HAIR_OPTIONS = [
  { key: "short", label: "Short" },
  { key: "ear-length", label: "Ear length" },
  { key: "medium", label: "Medium" },
  { key: "shoulder", label: "Shoulder" },
  { key: "long", label: "Long" },
];

const SMILE_OPTIONS = [
  { key: "neutral", label: "Neutral" },
  { key: "soft", label: "Soft" },
  { key: "slight-smile", label: "Slight" },
  { key: "smile", label: "Smile" },
  { key: "big-smile", label: "Big smile" },
];

const STEPS = [
  {
    n: "01",
    title: "Upload",
    body: "Drop 2–10 face photos and drag to set the order they morph through.",
  },
  {
    n: "02",
    title: "Preview",
    body: "Get a free low-res preview in seconds — no signup, no payment.",
  },
  {
    n: "03",
    title: "Render",
    body: "Pay once for a full cinematic 1080×1920 render, ready to share.",
  },
];

export default function Home() {
  return (
    <>
      <section className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-12 px-6 py-28 sm:py-36 lg:grid-cols-2 lg:gap-8">
        <div className="flex flex-col items-start gap-8">
          <p className="font-mono text-xs tracking-widest text-foreground/60 uppercase">
            AI face-morph video generator
          </p>
          <h1 className="max-w-3xl font-mono text-4xl leading-tight font-medium tracking-tight sm:text-6xl sm:leading-tight">
            Turn a sequence of photos into one morphing video.
          </h1>
          <p className="max-w-xl text-base text-foreground/70 sm:text-lg">
            Upload your face photos in order. We warp, blend, and AI-repair between every frame into a short
            cinematic video — free to preview, one payment to render in full.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="lg"
              className="h-11 px-6 font-mono uppercase tracking-wide"
              render={<Link href="/new">Start morphing</Link>}
            />
            <Button
              variant="outline"
              size="lg"
              className="h-11 px-6 font-mono uppercase tracking-wide"
              render={<Link href="#how-it-works">See how it works</Link>}
            />
          </div>
        </div>
        <div className="flex justify-center lg:justify-end">
          <HeroSlideshow />
        </div>
      </section>

      <section id="how-it-works" className="border-t border-border">
        <div className="mx-auto grid max-w-5xl grid-cols-1 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <div
              key={step.n}
              className={`flex flex-col gap-3 px-6 py-14 ${i > 0 ? "border-t border-border sm:border-t-0 sm:border-l" : ""}`}
            >
              <span className="font-mono text-xs text-foreground/50">{step.n}</span>
              <h3 className="font-mono text-lg uppercase tracking-wide">{step.title}</h3>
              <p className="text-sm text-foreground/70">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-24 text-center">
          <div className="flex flex-col items-center gap-4">
            <p className="font-mono text-xs tracking-widest text-foreground/60 uppercase">One face, every age</p>
            <h2 className="max-w-xl font-mono text-2xl tracking-tight sm:text-3xl">
              Drag the slider. Watch 40 years pass in one frame.
            </h2>
            <p className="max-w-md text-sm text-foreground/70">
              The same AI face-repair engine that powers your morph video can age a face forward or backward —
              scrub from 20 to 60 and see every year in between.
            </p>
          </div>
          <FaceMorphSlider folder="age-morph" min={20} max={60} step={10} label="AGE" />
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-24 text-center">
          <div className="flex flex-col items-center gap-4">
            <p className="font-mono text-xs tracking-widest text-foreground/60 uppercase">One face, every side</p>
            <h2 className="max-w-xl font-mono text-2xl tracking-tight sm:text-3xl">
              Turn the dial. Watch the same face rotate.
            </h2>
            <p className="max-w-md text-sm text-foreground/70">
              Our repair engine holds a face steady across viewpoints too — scrub from straight-on to a 40°
              turn and see the geometry hold up at every angle.
            </p>
          </div>
          <FaceMorphSlider folder="angle" min={0} max={40} step={10} unit="°" label="ANGLE" />
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-24 text-center">
          <div className="flex flex-col items-center gap-4">
            <p className="font-mono text-xs tracking-widest text-foreground/60 uppercase">One face, every length</p>
            <h2 className="max-w-xl font-mono text-2xl tracking-tight sm:text-3xl">
              Tap through. Same face, five hairstyles.
            </h2>
            <p className="max-w-md text-sm text-foreground/70">
              Hair is the hardest thing to keep consistent across a morph — our engine reconstructs it cleanly at
              every length, from a short crop to long waves.
            </p>
          </div>
          <SwitcherMorph folder="hair" options={HAIR_OPTIONS} altSuffix="hair" />
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-24 text-center">
          <div className="flex flex-col items-center gap-4">
            <p className="font-mono text-xs tracking-widest text-foreground/60 uppercase">One face, every mood</p>
            <h2 className="max-w-xl font-mono text-2xl tracking-tight sm:text-3xl">
              Tap through. Same face, five expressions.
            </h2>
            <p className="max-w-md text-sm text-foreground/70">
              Expression is often the first thing that breaks in a morph — our engine keeps the smile honest, from
              neutral all the way to a full grin.
            </p>
          </div>
          <SwitcherMorph folder="smile" options={SMILE_OPTIONS} altSuffix="expression" />
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col items-start gap-6 px-6 py-24">
          <h2 className="font-mono text-2xl tracking-tight sm:text-3xl">Ready to morph your photos?</h2>
          <Button
            size="lg"
            className="h-11 px-6 font-mono uppercase tracking-wide"
            render={<Link href="/new">Start morphing</Link>}
          />
          <p className="text-xs text-foreground/50">
            Source photos are deleted automatically after processing.
          </p>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-6 py-8 text-xs text-foreground/40">
          &copy; {new Date().getFullYear()} Morph
        </div>
      </footer>
    </>
  );
}
