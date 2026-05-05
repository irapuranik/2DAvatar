import { useRef, useState, useCallback, useEffect } from "react";

export interface MouthCue {
  start: number;
  end: number;
  value: string;
}

type QueuedChunk = {
  base64: string;
  seq: number;
  turnId: number;
  cues: MouthCue[];
};

function normalizeCues(raw: MouthCue[]): MouthCue[] {
  return raw.map((c) => ({
    start: Number(c.start),
    end: Number(c.end),
    value: String(c.value ?? "").trim(),
  }));
}

/** Rhubarb mouth shapes are A–H, X; tolerate lowercase / stray chars. */
function visemeFromCueValue(value: string): string | null {
  const v = value.toUpperCase().replace(/\s/g, "");
  const letter = v.charAt(0);
  if (/^[A-HX]$/.test(letter)) return letter;
  return null;
}

/**
 * MP3 queue with per-chunk Rhubarb cues (delivered with each `audio_chunk`).
 */
export function useAudioPlayback() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [mouthShape, setMouthShape] = useState("X");

  const queueRef = useRef<QueuedChunk[]>([]);
  const playingRef = useRef(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);
  const ctxRef = useRef<AudioContext | null>(null);
  const lastShapeRef = useRef("X");
  const lastShapeAtRef = useRef(0);
  const lastSpeechShapeAtRef = useRef(0);

  const cancelRaf = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
  }, []);

  const ensureContext = useCallback(() => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext();
    }
    if (ctxRef.current.state === "suspended") {
      ctxRef.current.resume();
    }
    return ctxRef.current;
  }, []);

  const runLipSync = useCallback((audio: HTMLAudioElement, cues: MouthCue[]) => {
    cancelRaf();
    let cueIdx = 0;
    const minHoldMs = 45;
    const lookahead = 0.012;
    const tick = () => {
      if (!audio || audio.ended) return;
      const t = audio.currentTime + lookahead;
      while (cueIdx < cues.length && t >= cues[cueIdx].end) {
        cueIdx += 1;
      }
      let nextShape = "X";
      if (cueIdx < cues.length) {
        const active = cues[cueIdx];
        if (active?.value) {
          const vis = visemeFromCueValue(active.value);
          const a0 = Number(active.start);
          const a1 = Number(active.end);
          if (vis && t >= a0 && t < a1) {
            nextShape = vis;
          }
        }
      }
      const now = performance.now();
      if (nextShape !== "X") {
        lastSpeechShapeAtRef.current = now;
      } else if (now - lastSpeechShapeAtRef.current <= 34) {
        // Hold the most recent speech shape through tiny timestamp gaps.
        nextShape = lastShapeRef.current;
      }
      if (nextShape !== lastShapeRef.current) {
        if (now - lastShapeAtRef.current >= minHoldMs) {
          lastShapeRef.current = nextShape;
          lastShapeAtRef.current = now;
          setMouthShape(nextShape);
        }
      }
      if (!audio.ended && !audio.paused) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [cancelRaf]);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false;
      setIsPlaying(false);
      setMouthShape("X");
      return;
    }

    const item = queueRef.current.shift()!;
    const binary = atob(item.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    currentAudioRef.current = audio;
    const cues = item.cues;
    audio.onended = () => {
      URL.revokeObjectURL(url);
      cancelRaf();
      currentAudioRef.current = null;
      lastShapeRef.current = "X";
      lastShapeAtRef.current = performance.now();
      lastSpeechShapeAtRef.current = 0;
      setMouthShape("X");
      playNext();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      cancelRaf();
      currentAudioRef.current = null;
      playNext();
    };

    audio.play().then(() => {
      if (cues.length > 0) {
        lastShapeRef.current = "X";
        lastShapeAtRef.current = performance.now();
        lastSpeechShapeAtRef.current = 0;
        runLipSync(audio, cues);
      } else {
        setMouthShape("X");
      }
    }).catch(() => {
      URL.revokeObjectURL(url);
      playNext();
    });
  }, [cancelRaf, runLipSync]);

  const enqueue = useCallback(
    (base64Mp3: string, seq: number, turnId: number, cues: MouthCue[]) => {
      queueRef.current.push({
        base64: base64Mp3,
        seq,
        turnId,
        cues: normalizeCues(cues),
      });
      if (!playingRef.current) {
        playingRef.current = true;
        setIsPlaying(true);
        playNext();
      }
    },
    [playNext],
  );

  const stop = useCallback(() => {
    queueRef.current = [];
    cancelRaf();
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    playingRef.current = false;
    setIsPlaying(false);
    lastShapeRef.current = "X";
    lastShapeAtRef.current = performance.now();
    lastSpeechShapeAtRef.current = 0;
    setMouthShape("X");
  }, [cancelRaf]);

  useEffect(() => () => cancelRaf(), [cancelRaf]);

  return {
    enqueue,
    stop,
    isPlaying,
    mouthShape,
    ensureContext,
  };
}
