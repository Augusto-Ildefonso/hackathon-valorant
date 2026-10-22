// VaváGym mark: angular G with a V inside and four crosshair ticks (Figma "Logo" page, option A,
// file nilg3f5kGOAgARvLbUf8ml). Keep in sync with public/favicon.svg.

export function Logo({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      fill="none"
      role="img"
      aria-label="VaváGym"
      className={className}
    >
      <path
        d="M102 40 L86 24 L42 24 L24 42 L24 86 L42 104 L86 104 L104 86 L104 66 L70 66"
        className="stroke-accent"
        strokeWidth={11}
        strokeLinejoin="miter"
        strokeMiterlimit={10}
      />
      <polygon points="40,40 56,40 64,60 72,40 88,40 72,88 56,88" className="fill-fg" />
      <path d="M62 6h4v10h-4zM62 112h4v10h-4zM6 62h10v4H6zM112 62h10v4h-10z" className="fill-fg" />
    </svg>
  );
}
