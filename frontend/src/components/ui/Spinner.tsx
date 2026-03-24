import { AMBER } from "../../design/tokens";

interface SpinnerProps {
  size?: number;
  color?: string;
}

export default function Spinner({ size = 16, color = AMBER }: SpinnerProps) {
  return (
    <span
      style={{
        display: "inline-block",
        fontSize: size,
        color,
        animation: "pulse 1s ease-in-out infinite",
      }}
    >
      ◈
    </span>
  );
}
