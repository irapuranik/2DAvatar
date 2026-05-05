import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import Avatar from "@mui/material/Avatar";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import {
  Send, Mic, MicOff, ArrowLeft, Volume2, VolumeX, User, CheckCircle,
} from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";
import { CaseDetail } from "../stores/caseStore";
import { useConversation, ChatMessage, ConnectionStatus, AudioChunkPayload } from "../hooks/useConversation";
import { useAudioPlayback, type MouthCue } from "../hooks/useAudioPlayback";
import { useAvatarMotion } from "../hooks/useAvatarMotion";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { PrimaryButton, SmallText } from "../components/styled";
import PatientAvatar2D from "../components/PatientAvatar2D";

export default function PracticeSession() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();
  const backPath = user?.role === "admin" ? "/admin" : "/student";

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [muted, setMuted] = useState(false);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Audio playback + lip-sync mouth shape
  const { enqueue, stop: stopAudio, isPlaying, mouthShape, ensureContext } = useAudioPlayback();

  const {
    messages, isConnected, connectionStatus, isThinking,
    connect, disconnect, sendText, sendAudio, resetConversation,
  } = useConversation({
    token,
    caseId: caseId || null,
    onAudioChunk: useCallback(
      (chunk: AudioChunkPayload) => {
        if (!muted) {
          enqueue(
            chunk.data,
            chunk.seq,
            chunk.turn_id,
            (chunk.cues ?? []) as MouthCue[],
          );
        }
      },
      [muted, enqueue],
    ),
  });

  const latestAssistantText = [...messages]
    .reverse()
    .find((m) => m.role === "assistant")?.content || "";
  const avatarMotion = useAvatarMotion({
    isPlaying,
    isThinking,
    latestAssistantText,
  });

  // Voice recording
  const { isRecording, hasPermission, startRecording, stopRecording } = useVoiceRecorder(
    useCallback(
      (base64Audio: string) => {
        ensureContext(); // Ensure AudioContext for playback
        sendAudio(base64Audio);
      },
      [sendAudio, ensureContext],
    ),
  );

  // Load case details and check practice status
  useEffect(() => {
    if (!token || !caseId) return;
    (async () => {
      try {
        const detail = await apiFetch<CaseDetail>(`/cases/${caseId}`, { token });
        setCaseData(detail);
        // Check if already submitted
        if (user?.role === "student") {
          const sessions = await apiFetch<Array<{ case_id: string; status: string }>>(
            "/practice/my", { token }
          );
          const thisSession = sessions.find((s) => s.case_id === caseId);
          if (thisSession?.status === "submitted") {
            setIsSubmitted(true);
          }
        }
      } catch (err: any) {
        setLoadError(err.message || "Failed to load case");
      }
    })();
  }, [token, caseId]);

  // Connect WebSocket once case loads
  useEffect(() => {
    if (!caseData) return;

    connect();

    return () => {
      disconnect();
      stopAudio();
    };
  }, [caseData, connect, disconnect, stopAudio]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Re-focus text input whenever thinking ends (AI response complete)
  useEffect(() => {
    if (isConnected && !isThinking && !isRecording) {
      // Small delay to let the DOM settle after response renders
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [isThinking, isConnected, isRecording]);

  const handleSend = () => {
    if (!input.trim()) return;
    ensureContext();
    sendText(input);
    setInput("");
    // Keep focus on input after sending
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = () => {
    stopAudio();
    resetConversation();
  };

  const handleSubmit = async () => {
    if (!token || !caseId) return;
    setSubmitting(true);
    try {
      await apiFetch(`/practice/${caseId}/submit`, { method: "POST", token });
      setIsSubmitted(true);
      setSubmitDialogOpen(false);
      // Disconnect since the interview is done
      disconnect();
      stopAudio();
    } catch {
      // silently fail
    } finally {
      setSubmitting(false);
    }
  };

  // ── Loading / error states ──
  if (loadError) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography color="error" gutterBottom>{loadError}</Typography>
        <PrimaryButton onClick={() => navigate(backPath)}>
          Back to cases
        </PrimaryButton>
      </Box>
    );
  }

  if (!caseData) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Loading case...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 72px)" }}>
      {/* ── Header bar ── */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Tooltip title="Back to cases">
          <IconButton size="small" onClick={() => navigate(backPath)}>
            <ArrowLeft size={18} />
          </IconButton>
        </Tooltip>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            {caseData.title}
          </Typography>
          {caseData.patient_name && (
            <SmallText>Patient: {caseData.patient_name}</SmallText>
          )}
        </Box>
        <Chip
          size="small"
          label={
            connectionStatus === "connected"
              ? "Connected"
              : connectionStatus === "reconnecting"
              ? "Reconnecting..."
              : "Disconnected"
          }
          color={
            connectionStatus === "connected"
              ? "success"
              : connectionStatus === "reconnecting"
              ? "warning"
              : "error"
          }
          variant="outlined"
          sx={{ fontSize: "0.7rem" }}
        />
        <Tooltip title={muted ? "Unmute audio" : "Mute audio"}>
          <IconButton size="small" onClick={() => { setMuted(!muted); if (!muted) stopAudio(); }}>
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </IconButton>
        </Tooltip>
      </Box>

      {/* ── Main content area — vertical layout: image top, chat below ── */}
      <Box sx={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
        {/* ── Top: 2D Rhubarb avatar (not photo) ── */}
        <PatientAvatar2D
          mouthShape={mouthShape}
          patientName={caseData.patient_name}
          isPlaying={isPlaying}
          isThinking={isThinking}
          shapesBaseUrl={caseData?.viseme_shapes_base_url || "/static/shapes/"}
          headXDeg={avatarMotion.headXDeg}
          headYDeg={avatarMotion.headYDeg}
          headTiltDeg={avatarMotion.headTiltDeg}
          eyeOffsetX={avatarMotion.eyeOffsetX}
          eyeOffsetY={avatarMotion.eyeOffsetY}
        />

        {/* ── Bottom: Chat panel (full width) ── */}
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            maxWidth: 800,
            width: "100%",
            mx: "auto",
          }}
        >
          {/* Messages */}
          <Box
            sx={{
              flex: 1,
              overflow: "auto",
              px: 2,
              py: 2,
              display: "flex",
              flexDirection: "column",
              gap: 1.5,
            }}
          >
            {/* Welcome message */}
            {messages.length === 0 && (
              <Box sx={{ textAlign: "center", py: 4 }}>
                {caseData.patient_name && (
                  <Avatar
                    sx={{
                      width: 64,
                      height: 64,
                      bgcolor: "secondary.main",
                      mx: "auto",
                      mb: 2,
                    }}
                  >
                    <User size={28} />
                  </Avatar>
                )}
                <Typography variant="body2" color="text.secondary">
                  Start the conversation by typing a message or using voice input.
                </Typography>
                {caseData.description && (
                  <Typography variant="caption" color="text.disabled" sx={{ mt: 1, display: "block" }}>
                    {caseData.description}
                  </Typography>
                )}
              </Box>
            )}

            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} patientName={caseData.patient_name} />
            ))}

            {isThinking && (
              <Box sx={{ display: "flex", gap: 1, alignItems: "center", pl: 1 }}>
                <CircularProgress size={14} />
                <Typography variant="caption" color="text.secondary">
                  {caseData.patient_name || "Patient"} is thinking...
                </Typography>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>

          {/* Connection status banner */}
          {connectionStatus === "reconnecting" && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                px: 2,
                py: 1,
                bgcolor: "warning.main",
                color: "warning.contrastText",
              }}
            >
              <CircularProgress size={14} color="inherit" />
              <Typography variant="caption" fontWeight={600}>
                Connection lost. Reconnecting...
              </Typography>
            </Box>
          )}
          {connectionStatus === "disconnected" && caseData && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                px: 2,
                py: 1,
                bgcolor: "error.main",
                color: "error.contrastText",
              }}
            >
              <Typography variant="caption" fontWeight={600}>
                Disconnected.
              </Typography>
              <Typography
                variant="caption"
                sx={{ textDecoration: "underline", cursor: "pointer" }}
                onClick={connect}
              >
                Reconnect
              </Typography>
            </Box>
          )}

          {/* Input bar */}
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-end",
              gap: 1,
              px: 2,
              py: 1.5,
              borderTop: 1,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            {/* Mic button — hold to record */}
            <Tooltip title={
              hasPermission === false
                ? "Microphone access denied"
                : isRecording
                ? "Release to send"
                : "Hold to record"
            }>
              <IconButton
                color={isRecording ? "error" : "default"}
                onMouseDown={() => { if (!isRecording) startRecording(); }}
                onMouseUp={() => { if (isRecording) stopRecording(); }}
                onMouseLeave={() => { if (isRecording) stopRecording(); }}
                onTouchStart={() => { if (!isRecording) startRecording(); }}
                onTouchEnd={() => { if (isRecording) stopRecording(); }}
                disabled={!isConnected || isThinking}
                sx={{
                  transition: "all 0.2s",
                  ...(isRecording && {
                    bgcolor: "error.main",
                    color: "#fff",
                    "&:hover": { bgcolor: "error.dark" },
                    animation: "pulse 1.5s infinite",
                    "@keyframes pulse": {
                      "0%": { boxShadow: "0 0 0 0 rgba(211, 47, 47, 0.4)" },
                      "70%": { boxShadow: "0 0 0 10px rgba(211, 47, 47, 0)" },
                      "100%": { boxShadow: "0 0 0 0 rgba(211, 47, 47, 0)" },
                    },
                  }),
                }}
              >
                {isRecording ? <Mic size={20} /> : <MicOff size={20} />}
              </IconButton>
            </Tooltip>

            <TextField
              fullWidth
              size="small"
              inputRef={inputRef}
              autoFocus
              placeholder={isRecording ? "Recording..." : "Type a message..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isConnected || isThinking || isRecording}
              multiline
              maxRows={3}
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: 3,
                },
              }}
            />

            <IconButton
              color="primary"
              onClick={handleSend}
              disabled={!input.trim() || !isConnected || isThinking || isSubmitted}
            >
              <Send size={20} />
            </IconButton>

            {/* Submit interview button */}
            {user?.role === "student" && !isSubmitted && (
              <Tooltip title="Submit interview">
                <IconButton
                  color="success"
                  onClick={() => setSubmitDialogOpen(true)}
                  disabled={messages.length === 0}
                  sx={{
                    border: 1,
                    borderColor: "success.main",
                    borderRadius: 2,
                    ml: 0.5,
                  }}
                >
                  <CheckCircle size={20} />
                </IconButton>
              </Tooltip>
            )}
          </Box>

          {/* Submitted banner */}
          {isSubmitted && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                px: 2,
                py: 1.5,
                bgcolor: "success.main",
                color: "success.contrastText",
              }}
            >
              <CheckCircle size={16} />
              <Typography variant="body2" fontWeight={600}>
                Interview submitted
              </Typography>
              <Button
                size="small"
                variant="outlined"
                sx={{ ml: 2, color: "inherit", borderColor: "inherit", textTransform: "none" }}
                onClick={() => navigate(backPath)}
              >
                Back to cases
              </Button>
            </Box>
          )}
        </Box>
      </Box>

      {/* Submit confirmation dialog */}
      <Dialog open={submitDialogOpen} onClose={() => !submitting && setSubmitDialogOpen(false)}>
        <DialogTitle>Submit interview?</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            Are you sure you want to submit this interview? This will mark the case as
            completed. You can still review the conversation afterward, but you'll need
            to reset to start over.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSubmitDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            color="success"
            variant="contained"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "Submit"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// ── Message bubble sub-component ──

function MessageBubble({
  message,
  patientName,
}: {
  message: ChatMessage;
  patientName: string | null;
}) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <Box sx={{ textAlign: "center", py: 0.5 }}>
        <Typography variant="caption" color="text.disabled" fontStyle="italic">
          {message.content}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
      }}
    >
      <Paper
        elevation={0}
        sx={{
          maxWidth: "70%",
          px: 2,
          py: 1.2,
          borderRadius: 2.5,
          bgcolor: isUser
            ? (theme: any) =>
                theme.palette.mode === "dark" ? "#1E5288" : "#0C234B"
            : "action.hover",
          color: isUser ? "#FFFFFF" : "text.primary",
          borderBottomRightRadius: isUser ? 4 : undefined,
          borderBottomLeftRadius: !isUser ? 4 : undefined,
        }}
      >
        <Typography variant="caption" fontWeight={600} sx={{ display: "block", mb: 0.3, opacity: 0.7 }}>
          {isUser ? "User" : (patientName || "Patient")}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
          {message.content}
        </Typography>
      </Paper>
    </Box>
  );
}
