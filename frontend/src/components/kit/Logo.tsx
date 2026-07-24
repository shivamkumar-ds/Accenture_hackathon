// v2.0 -- official mark, per explicit founder decision superseding
// DESIGN_SYSTEM.md v1.0's flat single-hue rule (see index.css's design
// tokens comment and 99_DECISIONS_LOG.md for the full reasoning). Same
// overall shape/sparkle motif as before, now filled with the approved
// indigo->violet gradient instead of a flat primary fill. This is a
// faithful match in color and spirit to the approved reference mark, not
// a pixel-traced reproduction of its illustrated glyph -- reproducing
// that exactly would mean hand-authoring a complex multi-shaded path,
// which is a much bigger (and riskier) undertaking than this simple
// rounded-badge treatment already used everywhere the mark appears.
//
// The gradient id is generated per-instance via useId() -- this mark
// renders multiple times on the same page (sidebar, navbar, footer,
// login), and SVG gradients defined with a hardcoded id can misbehave
// across duplicate inline <svg> elements sharing that id.

import { useId } from "react";

export function LogoMark({ size = 28 }: { size?: number }) {
  const gradientId = useId();

  return (
    // aria-hidden: decorative when paired with the "BidOps" wordmark
    // (Logo, below) that already conveys the same information as text --
    // RC-1 audit finding C1. Where LogoMark is ever used alone with no
    // adjacent text, a caller should add its own aria-label instead.
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0" className="[stop-color:hsl(var(--logo-gradient-from))]" />
          <stop offset="1" className="[stop-color:hsl(var(--logo-gradient-to))]" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      <path
        d="M11 7h6.5a4 4 0 0 1 2.2 7.35A4.5 4.5 0 0 1 17.5 23H11V7Zm3 3v4.5h3a2.25 2.25 0 0 0 0-4.5h-3Zm0 7.5V20h3.5a2.25 2.25 0 0 0 0-4.5H14Z"
        fill="white"
        fillOpacity="0.95"
      />
      <path
        d="M24 6.5c.25 1.3.95 2 2.25 2.25-1.3.25-2 .95-2.25 2.25-.25-1.3-.95-2-2.25-2.25 1.3-.25 2-.95 2.25-2.25Z"
        fill="white"
      />
      <path
        d="M21.5 15.5c.18.95.68 1.45 1.63 1.63-.95.18-1.45.68-1.63 1.63-.18-.95-.68-1.45-1.63-1.63.95-.18 1.45-.68 1.63-1.63Z"
        fill="white"
        fillOpacity="0.85"
      />
    </svg>
  );
}

export function Logo({ size = 22, wordmarkClassName = "" }: { size?: number; wordmarkClassName?: string }) {
  return (
    <div className="flex items-center gap-2">
      <LogoMark size={size} />
      <span className={`font-semibold tracking-tight ${wordmarkClassName}`}>BidOps</span>
    </div>
  );
}
