import { useRef, useState, useCallback, useEffect } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

export interface AudioChunkPayload {
  data: string;
  seq: number;
  turn_id: number;
  cues: Array<{ start: number; end: number; value: string }>;
}

interface UseConversationOptions {
  token: string | null;
  caseId: string | null;
  onAudioChunk?: (chunk: AudioChunkPayload) => void;
  onAudioEnd?: () => void;
  onResponseText?: (text: string) => void;
}

export type ConnectionStatus = "disconnected" | "connected" | "reconnecting";

function parseWsInt(v: unknown, defaultVal: number): number {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return defaultVal;
}

export function useConversation(opts: UseConversationOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [isThinking, setIsThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const optsRef = useRef(opts);
  optsRef.current = opts;
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const MAX_RECONNECT_ATTEMPTS = 3;
  const streamingAssistantIdRef = useRef<string | null>(null);

  const addMessage = useCallback(
    (role: ChatMessage["role"], content: string) => {
      const msg: ChatMessage = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
        timestamp: Date.now(),
      };
      setMessages((prev) => {
        // Guard against duplicated assistant frames/events from websocket retries.
        if (role === "assistant" && prev.length > 0) {
          const last = prev[prev.length - 1];
          if (last.role === "assistant" && last.content.trim() === content.trim()) {
            return prev;
          }
        }
        return [...prev, msg];
      });
      return msg;
    },
    [],
  );

  const connect = useCallback(() => {
    const { token, caseId } = optsRef.current;
    if (!token || !caseId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Build WebSocket URL — use VITE_API_URL for deployed split-host setup
    const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
    const parsedUrl = new URL(apiUrl);
    const wsProto = parsedUrl.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${parsedUrl.host}/ws/conversation`;

    if (import.meta.env.DEV) console.log("[WS] Connecting to:", wsUrl);
    intentionalCloseRef.current = false;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (import.meta.env.DEV) console.log("[WS] Connected, sending auth");
      // Send auth as first message — keeps token out of server access logs
      ws.send(JSON.stringify({ type: "auth", token, case_id: caseId }));
      setConnectionStatus("connected");
      reconnectAttemptRef.current = 0; // Reset retry counter on successful connect
    };

    ws.onclose = (e) => {
      if (import.meta.env.DEV) console.log("[WS] Closed:", e.code, e.reason);
      wsRef.current = null;

      // If we closed intentionally (disconnect/unmount), don't reconnect
      if (intentionalCloseRef.current) {
        setConnectionStatus("disconnected");
        return;
      }

      // Auto-reconnect on unexpected close (up to MAX_RECONNECT_ATTEMPTS)
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptRef.current += 1;
        const delay = reconnectAttemptRef.current * 2000; // 2s, 4s, 6s
        if (import.meta.env.DEV) console.log(`[WS] Reconnecting (attempt ${reconnectAttemptRef.current}/${MAX_RECONNECT_ATTEMPTS}) in ${delay}ms`);
        setConnectionStatus("reconnecting");
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        if (import.meta.env.DEV) console.log("[WS] Max reconnect attempts reached");
        setConnectionStatus("disconnected");
      }
    };

    ws.onerror = (e) => {
      if (import.meta.env.DEV) console.error("[WS] Error:", e);
      ws.close();
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);

        switch (data.type) {
          case "history": {
            // Restore prior conversation from DB
            streamingAssistantIdRef.current = null;
            const restored: ChatMessage[] = (data.messages as { role: string; content: string }[]).map(
              (m, i) => ({
                id: `hist-${i}`,
                role: m.role as ChatMessage["role"],
                content: m.content,
                timestamp: 0,
              })
            );
            setMessages(restored);
            break;
          }

          case "transcript":
            // Student's voice was transcribed — show as user message
            addMessage("user", data.content);
            break;

          case "response_stream": {
            const content = String(data.content ?? "");
            setIsThinking(false);
            setMessages((prev) => {
              const sid = streamingAssistantIdRef.current;
              if (sid) {
                const i = prev.findIndex((m) => m.id === sid);
                if (i >= 0) {
                  const next = [...prev];
                  next[i] = { ...next[i], content };
                  return next;
                }
              }
              const id = `assistant-stream-${Date.now()}`;
              streamingAssistantIdRef.current = id;
              return [
                ...prev,
                { id, role: "assistant" as const, content, timestamp: Date.now() },
              ];
            });
            break;
          }

          case "response_text":
            setIsThinking(false);
            {
              const content = String(data.content ?? "");
              const sid = streamingAssistantIdRef.current;
              streamingAssistantIdRef.current = null;
              if (sid) {
                setMessages((prev) => {
                  const i = prev.findIndex((m) => m.id === sid);
                  if (i >= 0) {
                    const next = [...prev];
                    next[i] = { ...next[i], content };
                    return next;
                  }
                  if (prev.length > 0) {
                    const last = prev[prev.length - 1];
                    if (last.role === "assistant" && last.content.trim() === content.trim()) {
                      return prev;
                    }
                  }
                  return [
                    ...prev,
                    { id: `${Date.now()}-a`, role: "assistant" as const, content, timestamp: Date.now() },
                  ];
                });
              } else {
                addMessage("assistant", content);
              }
              optsRef.current.onResponseText?.(content);
            }
            break;

          case "audio_chunk":
            // Stop "thinking" as soon as speech is ready — text may still be streaming on the server.
            setIsThinking(false);
            optsRef.current.onAudioChunk?.({
              data: data.data,
              seq: parseWsInt(data.seq, 0),
              turn_id: parseWsInt(data.turn_id, 1),
              cues: Array.isArray(data.cues) ? data.cues : [],
            });
            break;

          case "audio_end":
            optsRef.current.onAudioEnd?.();
            break;

          case "info":
            // Don't show system info messages for restored sessions
            break;

          case "error":
            setIsThinking(false);
            streamingAssistantIdRef.current = null;
            addMessage("system", `Error: ${data.content}`);
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };
  }, [addMessage]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  /** Send a text message */
  const sendText = useCallback(
    (text: string) => {
      if (!text.trim() || wsRef.current?.readyState !== WebSocket.OPEN) return;
      addMessage("user", text.trim());
      setIsThinking(true);
      wsRef.current.send(JSON.stringify({ type: "text", content: text.trim() }));
    },
    [addMessage],
  );

  /** Send recorded audio as base64 */
  const sendAudio = useCallback((base64Audio: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    setIsThinking(true);
    wsRef.current.send(
      JSON.stringify({ type: "audio", audio_data: base64Audio }),
    );
  }, []);

  /** Reset conversation on backend */
  const resetConversation = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    streamingAssistantIdRef.current = null;
    wsRef.current.send(JSON.stringify({ type: "reset" }));
    setMessages([]);
    setIsThinking(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalCloseRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, []);

  const isConnected = connectionStatus === "connected";

  return {
    messages,
    isConnected,
    connectionStatus,
    isThinking,
    connect,
    disconnect,
    sendText,
    sendAudio,
    resetConversation,
  };
}
