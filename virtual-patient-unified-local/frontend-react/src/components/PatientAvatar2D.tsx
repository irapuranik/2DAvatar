import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";

const SHAPES = new Set(["A", "B", "C", "D", "E", "F", "G", "H", "X"]);
const BLINK_SAFE_SPEECH_VISEMES = new Set(["X", "A", "B"]);

function normalizeShapesBase(url: string): string {
  const u = (url || "/static/shapes/").trim();
  return u.endsWith("/") ? u : `${u}/`;
}

function shapeSrc(base: string, shape: string): string {
  const b = normalizeShapesBase(base);
  if (shape === "blink") {
    return `${b}blink.png`;
  }
  const s = SHAPES.has(shape) ? shape : "X";
  return `${b}${s}.png`;
}

interface PatientAvatar2DProps {
  mouthShape: string;
  patientName?: string | null;
  isPlaying: boolean;
  isThinking: boolean;
  /** Base URL for viseme PNGs (trailing slash optional). Default `/static/shapes/`. Per-case: `/generated/cases/{id}/shapes/` */
  shapesBaseUrl?: string;
  headXDeg?: number;
  headYDeg?: number;
  headTiltDeg?: number;
  eyeOffsetX?: number;
  eyeOffsetY?: number;
}

/**
 * 2D Rhubarb-style mouth shapes (PNG assets in public/static/shapes).
 */
export default function PatientAvatar2D({
  mouthShape,
  patientName,
  isPlaying,
  isThinking,
  shapesBaseUrl = "/static/shapes/",
  headXDeg = 0,
  headYDeg = 0,
  headTiltDeg = 0,
  eyeOffsetX = 0,
  eyeOffsetY = 0,
}: PatientAvatar2DProps) {
  const baseViseme = mouthShape && SHAPES.has(mouthShape) ? mouthShape : "X";

  /** Local blink so it is not overwritten by parent RAF-driven state updates. */
  const [isBlinking, setIsBlinking] = useState(false);
  const blinkMountedRef = useRef(true);
  const blinkIntervalRef = useRef(0);
  const blinkReleaseRef = useRef(0);
  const isPlayingRef = useRef(isPlaying);
  const currentVisemeRef = useRef(baseViseme);

  useEffect(() => {
    isPlayingRef.current = isPlaying;
    // If speech is on a wide-open viseme, avoid blink replacement frame.
    if (isPlaying && isBlinking && !BLINK_SAFE_SPEECH_VISEMES.has(baseViseme)) {
      setIsBlinking(false);
    }
  }, [isPlaying, isBlinking, baseViseme]);

  useEffect(() => {
    currentVisemeRef.current = baseViseme;
  }, [baseViseme]);

  useEffect(() => {
    blinkMountedRef.current = true;
    const PERIOD_MS = 2000;
    const LID_MS = 100;

    const pulse = () => {
      if (!blinkMountedRef.current) return;
      const speaking = isPlayingRef.current;
      const safeDuringSpeech = BLINK_SAFE_SPEECH_VISEMES.has(currentVisemeRef.current);
      // Permit blink during speech only on closed/near-closed mouth visemes.
      if (speaking && !safeDuringSpeech) return;
      window.clearTimeout(blinkReleaseRef.current);
      setIsBlinking(true);
      blinkReleaseRef.current = window.setTimeout(() => {
        if (blinkMountedRef.current) setIsBlinking(false);
      }, LID_MS);
    };

    blinkIntervalRef.current = window.setInterval(pulse, PERIOD_MS);
    pulse();

    return () => {
      blinkMountedRef.current = false;
      window.clearInterval(blinkIntervalRef.current);
      window.clearTimeout(blinkReleaseRef.current);
    };
  }, []);

  const viseme = isBlinking ? "blink" : (isPlaying ? baseViseme : "X");

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        py: 2.5,
        px: 2,
        flexShrink: 0,
        bgcolor: (theme: { palette: { mode: string } }) =>
          theme.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "#f5f7fa",
        borderBottom: 1,
        borderColor: "divider",
        position: "relative",
      }}
    >
      {/* Fixed square stage so every PNG is scaled the same way; tune objectPosition if faces still drift. */}
      <Box
        sx={{
          width: { xs: 120, sm: 150, md: 170 },
          height: { xs: 120, sm: 150, md: 170 },
          position: "relative",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 2,
          boxShadow: "0 2px 12px rgba(0,0,0,0.1)",
          overflow: "hidden",
          isolation: "isolate",
          bgcolor: (theme: { palette: { mode: string } }) =>
            theme.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(0,0,0,0.04)",
        }}
      >
        <Box
          component="img"
          key={isBlinking ? "blink" : "viseme"}
          src={shapeSrc(shapesBaseUrl, viseme)}
          alt={patientName || "Patient"}
          sx={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: `calc(50% + ${eyeOffsetX}px) calc(28% + ${eyeOffsetY}px)`,
            transform: `
              perspective(700px)
              rotateY(${headXDeg}deg)
              rotateX(${-headYDeg}deg)
              rotate(${headTiltDeg}deg)
              scale(1.06)
              translateZ(0)
            `,
            transformOrigin: "center center",
            display: "block",
            transition: isBlinking
              ? "transform 48ms linear"
              : "object-position 46ms linear, transform 48ms linear",
            willChange: "object-position, transform",
          }}
        />
      </Box>

      <Typography variant="h6" fontWeight={600} sx={{ mt: 1.5 }}>
        {patientName || "Patient"}
      </Typography>

      {isPlaying && (
        <Chip
          size="small"
          label="Speaking..."
          color="secondary"
          sx={{ fontSize: "0.65rem", height: 20, mt: 0.5 }}
        />
      )}
      {isThinking && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.5 }}>
          <CircularProgress size={12} />
          <Typography variant="caption" color="text.secondary">
            Thinking...
          </Typography>
        </Box>
      )}
    </Box>
  );
}
