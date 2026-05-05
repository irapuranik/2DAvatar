import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import ListItemAvatar from "@mui/material/ListItemAvatar";
import Avatar from "@mui/material/Avatar";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Divider from "@mui/material/Divider";
import Button from "@mui/material/Button";
import {
  ArrowLeft, User, FileText, Download, MessageSquare, Clock,
} from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";
import { SmallText } from "./styled";

interface StudentSummary {
  id: string;
  email: string;
  display_name: string;
  submitted_count: number;
}

interface SessionSummary {
  id: string;
  case_id: string;
  case_title: string;
  patient_name: string | null;
  status: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

interface TranscriptData {
  session_id: string;
  student_name: string;
  student_email: string;
  case_title: string;
  patient_name: string | null;
  status: string;
  messages: Array<{ role: string; content: string }>;
  created_at: string | null;
  updated_at: string | null;
}

type View = "students" | "sessions" | "transcript";

export default function Transcripts() {
  const { token } = useAuthStore();

  const [view, setView] = useState<View>("students");
  const [loading, setLoading] = useState(false);

  // Data
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<StudentSummary | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionSummary | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);

  // Load students on mount
  useEffect(() => {
    if (!token) return;
    setLoading(true);
    apiFetch<StudentSummary[]>("/practice/admin/students", { token })
      .then(setStudents)
      .catch(() => setStudents([]))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSelectStudent = async (student: StudentSummary) => {
    if (!token) return;
    setSelectedStudent(student);
    setView("sessions");
    setLoading(true);
    try {
      const data = await apiFetch<SessionSummary[]>(
        `/practice/admin/students/${student.id}/sessions`,
        { token }
      );
      setSessions(data);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSession = async (session: SessionSummary) => {
    if (!token) return;
    setSelectedSession(session);
    setView("transcript");
    setLoading(true);
    try {
      const data = await apiFetch<TranscriptData>(
        `/practice/admin/sessions/${session.id}/transcript`,
        { token }
      );
      setTranscript(data);
    } catch {
      setTranscript(null);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    if (view === "transcript") {
      setView("sessions");
      setTranscript(null);
      setSelectedSession(null);
    } else if (view === "sessions") {
      setView("students");
      setSessions([]);
      setSelectedStudent(null);
    }
  };

  const handleDownload = () => {
    if (!transcript) return;

    // Build numbered format: 1::Coach:: message2::Partner:: message...
    const parts: string[] = [];
    transcript.messages.forEach((msg, i) => {
      const num = i + 1;
      const role = msg.role === "user" ? "Coach" : "Partner";
      parts.push(`${num}::${role}:: ${msg.content}`);
    });
    const text = parts.join("\n");

    const dateStr = transcript.updated_at
      ? new Date(transcript.updated_at).toLocaleDateString("en-US", {
          month: "2-digit", day: "2-digit", year: "numeric",
        }).replace(/\//g, "-")
      : "unknown";
    const patientName = transcript.patient_name || "patient";

    const blob = new Blob([text], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `transcript_${transcript.student_name}_${dateStr}_${patientName}.txt`
      .replace(/\s+/g, "_");
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const statusColor = (s: string): "success" | "info" | "default" => {
    if (s === "submitted") return "success";
    if (s === "in_progress") return "info";
    return "default";
  };

  const statusLabel = (s: string): string => {
    if (s === "submitted") return "Submitted";
    if (s === "in_progress") return "In progress";
    if (s === "not_started") return "Not started";
    return s;
  };

  return (
    <Box>
      {/* Header with breadcrumb navigation */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
        {view !== "students" && (
          <Tooltip title="Back">
            <IconButton size="small" onClick={handleBack}>
              <ArrowLeft size={18} />
            </IconButton>
          </Tooltip>
        )}
        <Box>
          <Typography variant="h6" fontWeight={600}>
            {view === "students" && "Student Transcripts"}
            {view === "sessions" && `${selectedStudent?.display_name}'s Sessions`}
            {view === "transcript" && `${selectedSession?.case_title}`}
          </Typography>
          <SmallText>
            {view === "students" && "Select a student to view their submitted interviews"}
            {view === "sessions" && `${selectedStudent?.email}`}
            {view === "transcript" &&
              `${transcript?.student_name} — ${formatDate(transcript?.updated_at || null)}`}
          </SmallText>
        </Box>
        {view === "transcript" && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<Download size={14} />}
            onClick={handleDownload}
            sx={{ ml: "auto", textTransform: "none" }}
          >
            Download .txt
          </Button>
        )}
      </Box>

      {loading ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* ── Student list ── */}
          {view === "students" && (
            students.length === 0 ? (
              <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
                <FileText size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No transcripts yet
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Transcripts will appear here once students submit their interviews.
                </Typography>
              </Paper>
            ) : (
              <Paper sx={{ borderRadius: 2 }}>
                <List disablePadding>
                  {students.map((stu, idx) => (
                    <Box key={stu.id}>
                      {idx > 0 && <Divider />}
                      <ListItemButton onClick={() => handleSelectStudent(stu)} sx={{ py: 2 }}>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: "primary.main" }}>
                            <User size={20} />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Typography variant="body1" fontWeight={500}>
                              {stu.display_name}
                            </Typography>
                          }
                          secondary={stu.email}
                        />
                        <Chip
                          size="small"
                          label={`${stu.submitted_count} submitted`}
                          color="success"
                          variant="outlined"
                          sx={{ mr: 1 }}
                        />
                      </ListItemButton>
                    </Box>
                  ))}
                </List>
              </Paper>
            )
          )}

          {/* ── Session list for selected student ── */}
          {view === "sessions" && (
            sessions.length === 0 ? (
              <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
                <MessageSquare size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No sessions found
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  This student hasn't started any practice sessions yet.
                </Typography>
              </Paper>
            ) : (
              <Paper sx={{ borderRadius: 2 }}>
                <List disablePadding>
                  {sessions.map((sess, idx) => (
                    <Box key={sess.id}>
                      {idx > 0 && <Divider />}
                      <ListItemButton
                        onClick={() => handleSelectSession(sess)}
                        sx={{ py: 2 }}
                        disabled={sess.message_count === 0}
                      >
                        <ListItemAvatar>
                          <Avatar
                            sx={{
                              bgcolor:
                                sess.status === "submitted"
                                  ? "success.main"
                                  : sess.status === "in_progress"
                                  ? "info.main"
                                  : "action.hover",
                            }}
                          >
                            <MessageSquare size={20} />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Typography variant="body1" fontWeight={500}>
                              {sess.case_title}
                            </Typography>
                          }
                          secondary={
                            <Box
                              component="span"
                              sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}
                            >
                              <Clock size={12} />
                              {formatDate(sess.updated_at)}
                              {sess.patient_name && ` · Patient: ${sess.patient_name}`}
                            </Box>
                          }
                        />
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Chip
                            size="small"
                            label={`${sess.message_count} messages`}
                            variant="outlined"
                          />
                          <Chip
                            size="small"
                            label={statusLabel(sess.status)}
                            color={statusColor(sess.status)}
                          />
                        </Box>
                      </ListItemButton>
                    </Box>
                  ))}
                </List>
              </Paper>
            )
          )}

          {/* ── Transcript view ── */}
          {view === "transcript" && transcript && (
            <Paper
              sx={{
                borderRadius: 2,
                maxHeight: "calc(100vh - 280px)",
                overflow: "auto",
              }}
            >
              <Box sx={{ p: 3 }}>
                {/* Metadata header */}
                <Box
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 1,
                    mb: 3,
                    pb: 2,
                    borderBottom: 1,
                    borderColor: "divider",
                  }}
                >
                  <Chip size="small" label={`Student: ${transcript.student_name}`} />
                  <Chip size="small" label={`Case: ${transcript.case_title}`} />
                  {transcript.patient_name && (
                    <Chip size="small" label={`Patient: ${transcript.patient_name}`} />
                  )}
                  <Chip
                    size="small"
                    label={statusLabel(transcript.status)}
                    color={statusColor(transcript.status)}
                  />
                  <Chip size="small" label={`${transcript.messages.length} messages`} variant="outlined" />
                </Box>

                {/* Messages */}
                {transcript.messages.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 4 }}>
                    No messages in this session.
                  </Typography>
                ) : (
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    {transcript.messages.map((msg, i) => {
                      const isUser = msg.role === "user";
                      const label = isUser ? "Coach" : "Partner";
                      return (
                        <Box key={i}>
                          <Typography
                            variant="caption"
                            fontWeight={700}
                            color={isUser ? "primary.main" : "secondary.main"}
                            sx={{ mb: 0.3, display: "block" }}
                          >
                            {label}
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{
                              whiteSpace: "pre-wrap",
                              lineHeight: 1.6,
                              pl: 1.5,
                              borderLeft: 3,
                              borderColor: isUser ? "primary.main" : "secondary.main",
                              py: 0.5,
                            }}
                          >
                            {msg.content}
                          </Typography>
                        </Box>
                      );
                    })}
                  </Box>
                )}
              </Box>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
}
