import { useEffect, useRef, useState } from "react";

export interface AvatarMotionState {
  headXDeg: number;
  headYDeg: number;
  headTiltDeg: number;
  eyeOffsetX: number;
  eyeOffsetY: number;
}

interface UseAvatarMotionOptions {
  isPlaying: boolean;
  isThinking: boolean;
  latestAssistantText: string;
}

/**
 * Lightweight idle motion so the avatar can nod/tilt while speaking or thinking.
 * Motion remains subtle to avoid artifacts in 2D layered assets.
 */
export function useAvatarMotion(opts: UseAvatarMotionOptions): AvatarMotionState {
  const { isPlaying, isThinking, latestAssistantText } = opts;
  const [motion, setMotion] = useState<AvatarMotionState>({
    headXDeg: 0,
    headYDeg: 0,
    headTiltDeg: 0,
    eyeOffsetX: 0,
    eyeOffsetY: 0,
  });
  const motionRef = useRef(motion);
  const gestureRef = useRef<{
    kind: "nod" | "shake" | null;
    startedAtMs: number;
    durationMs: number;
  }>({
    kind: null,
    startedAtMs: 0,
    durationMs: 0,
  });
  const lastAssistantTextRef = useRef("");

  useEffect(() => {
    motionRef.current = motion;
  }, [motion]);

  useEffect(() => {
    const text = (latestAssistantText || "").trim();
    if (!text || text === lastAssistantTextRef.current) return;
    lastAssistantTextRef.current = text;

    const lower = text.toLowerCase();
    const affirmative =
      /\b(yes|yeah|yep|absolutely|definitely|sure|of course|sounds good|great idea|that works|correct|exactly|agree)\b/.test(lower);
    const negative =
      /\b(no|nope|not really|don't|do not|can't|cannot|won't|wouldn't|isn't|aren't|incorrect|not possible|i disagree)\b/.test(lower);

    const now = performance.now();
    if (negative && !affirmative) {
      gestureRef.current = { kind: "shake", startedAtMs: now, durationMs: 1150 };
      return;
    }
    if (affirmative) {
      gestureRef.current = { kind: "nod", startedAtMs: now, durationMs: 1200 };
    }
  }, [latestAssistantText]);

  useEffect(() => {
    let rafId = 0;
    let start = 0;
    const damping = 0.16;
    const activity = isPlaying ? 1.18 : (isThinking ? 0.88 : 0.55);

    const tick = (now: number) => {
      if (!start) start = now;
      const t = (now - start) / 1000;

      let gestureX = 0;
      let gestureY = 0;
      const g = gestureRef.current;
      if (g.kind) {
        const elapsed = now - g.startedAtMs;
        const progress = elapsed / g.durationMs;
        if (progress >= 1) {
          gestureRef.current = { kind: null, startedAtMs: 0, durationMs: 0 };
        } else {
          // Smooth in/out envelope.
          const envelope = Math.sin(Math.PI * progress);
          if (g.kind === "nod") {
            // 2 quick nod cycles.
            gestureY = Math.sin(progress * Math.PI * 4) * 4.0 * envelope;
          } else if (g.kind === "shake") {
            // 3 quick shake cycles.
            gestureX = Math.sin(progress * Math.PI * 6) * 4.2 * envelope;
          }
        }
      }

      // Deliberate speaking nod (pitch-only): clear up/down motion while talking.
      const speakingNod = isPlaying ? (Math.sin(t * 5.2) * 2.4) : 0;
      // Reduce background Y bob during speech so the nod is the dominant motion.
      const baseYBob = Math.cos(t * 1.35 + 0.2) * (isPlaying ? 0.5 : 2.0) * activity;
      const targetX = (Math.sin(t * 0.68 + 0.4) * 1.6 * activity) + gestureX;
      const targetY = baseYBob + speakingNod + gestureY;
      const targetTilt = Math.sin(t * 0.95 - 0.3) * 1.0 * activity;

      const prev = motionRef.current;
      const next: AvatarMotionState = {
        headXDeg: prev.headXDeg + ((targetX - prev.headXDeg) * damping),
        headYDeg: prev.headYDeg + ((targetY - prev.headYDeg) * damping),
        headTiltDeg: prev.headTiltDeg + ((targetTilt - prev.headTiltDeg) * damping),
        eyeOffsetX: 0,
        eyeOffsetY: 0,
      };

      motionRef.current = next;
      setMotion(next);
      rafId = window.requestAnimationFrame(tick);
    };

    rafId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(rafId);
  }, [isPlaying, isThinking]);

  return motion;
}
