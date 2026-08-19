import { type CSSProperties, type ReactNode, useEffect, useState } from "react";

export function MotionPage({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`motion-page ${className}`}>{children}</div>;
}

export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  return <div className={`motion-reveal ${className}`} style={{ "--motion-delay": `${delay}ms` } as CSSProperties}>{children}</div>;
}

export function Stagger({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`motion-stagger ${className}`}>{children}</div>;
}

export function CountUp({ value, className = "" }: { value: number; className?: string }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const target = Number.isFinite(value) ? value : 0;
    if (target === 0) { setDisplay(0); return; }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / 520);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(target * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <span className={`motion-count ${className}`}>{display}</span>;
}
