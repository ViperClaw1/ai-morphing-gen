import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="font-mono text-sm tracking-widest uppercase">
          Morph
        </Link>
        <Button
          size="sm"
          className="font-mono uppercase tracking-wide"
          nativeButton={false}
          render={<Link href="/new">Start morphing</Link>}
        />
      </div>
    </header>
  );
}
