// Matches the mark's shape and sparkle motif from the earlier brand
// reference, but rendered as a flat single-hue fill instead of a
// gradient -- DESIGN_SYSTEM.md v1.0 explicitly avoids "flashy gradients"
// and purple/violet hues, so the previous indigo->violet gradient fill
// is replaced with the frozen deep-blue primary token. If real exported
// SVG/PNG/ICO assets become available, swap the <path> data below for
// the original.

export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    // aria-hidden: decorative when paired with the "BidOps AI" wordmark
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
      <rect width="32" height="32" rx="8" className="fill-primary" />
      <path
        d="M11 7h6.5a4 4 0 0 1 2.2 7.35A4.5 4.5 0 0 1 17.5 23H11V7Zm3 3v4.5h3a2.25 2.25 0 0 0 0-4.5h-3Zm0 7.5V20h3.5a2.25 2.25 0 0 0 0-4.5H14Z"
        fill="white"
        fillOpacity="0.95"
      />
      <path
        d="M24 6.5c.25 1.3.95 2 2.25 2.25-1.3.25-2 .95-2.25 2.25-.25-1.3-.95-2-2.25-2.25 1.3-.25 2-.95 2.25-2.25Z"
        fill="white"
      />
    </svg>
  );
}

export function Logo({ size = 22, wordmarkClassName = "" }: { size?: number; wordmarkClassName?: string }) {
  return (
    <div className="flex items-center gap-2">
      <LogoMark size={size} />
      <span className={`font-semibold tracking-tight ${wordmarkClassName}`}>
        BidOps <span className="text-brand-accent">AI</span>
      </span>
    </div>
  );
}
