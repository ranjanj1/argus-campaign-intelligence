interface BadgeProps {
  children: React.ReactNode;
  color: string;
}

export default function Badge({ children, color }: BadgeProps) {
  return (
    <span
      style={{
        background: `${color}18`,
        border: `1px solid ${color}33`,
        color,
        borderRadius: 4,
        padding: "1px 6px",
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: "0.06em",
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      {children}
    </span>
  );
}
