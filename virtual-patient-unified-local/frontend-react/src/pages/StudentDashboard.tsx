import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Card from "@mui/material/Card";
import CardMedia from "@mui/material/CardMedia";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import { MessageSquare, ClipboardList, Calendar, RotateCcw } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useCaseStore, CaseListItem } from "../stores/caseStore";
import { apiFetch } from "../api/client";
import {
  PageTitle, SmallText, SecondaryButton, PrimaryButton,
} from "../components/styled";

interface Assignment {
  id: string;
  student_id: string;
  case_id: string;
  due_date: string | null;
  status: "pending" | "in_progress" | "completed";
  completed_at: string | null;
  case_title: string | null;
}

interface PracticeSessionInfo {
  id: string;
  user_id: string;
  case_id: string;
  status: "not_started" | "in_progress" | "submitted";
  created_at: string;
  updated_at: string;
}

export default function StudentDashboard() {
  const { token } = useAuthStore();
  const { cases, isLoading: casesLoading, fetchCases } = useCaseStore();
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [assignmentsLoading, setAssignmentsLoading] = useState(true);
  const [practiceSessions, setPracticeSessions] = useState<PracticeSessionInfo[]>([]);
  const [practiceLoading, setPracticeLoading] = useState(true);
  const [resetDialogCase, setResetDialogCase] = useState<CaseListItem | null>(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    if (token) {
      fetchCases(token);
      apiFetch<Assignment[]>("/assignments/my", { token })
        .then(setAssignments)
        .catch(() => setAssignments([]))
        .finally(() => setAssignmentsLoading(false));
      apiFetch<PracticeSessionInfo[]>("/practice/my", { token })
        .then(setPracticeSessions)
        .catch(() => setPracticeSessions([]))
        .finally(() => setPracticeLoading(false));
    }
  }, [token]);

  const isLoading = casesLoading || assignmentsLoading || practiceLoading;

  // Build lookup maps
  const assignedCaseIds = new Set(assignments.map((a) => a.case_id));
  const assignmentByCase = new Map(assignments.map((a) => [a.case_id, a]));
  const practiceByCase = new Map(practiceSessions.map((p) => [p.case_id, p]));

  // Students only see cases assigned to them
  const assignedCases = cases.filter((c) => assignedCaseIds.has(c.id));

  const handleStartPractice = (c: CaseListItem) => {
    // Mark assignment as in_progress if it's currently pending
    const assignment = assignmentByCase.get(c.id);
    if (assignment && assignment.status === "pending" && token) {
      apiFetch(`/assignments/${assignment.id}`, {
        method: "PATCH",
        body: { status: "in_progress" },
        token,
      }).catch(() => {}); // fire and forget
    }
    navigate(`/student/practice/${c.id}`);
  };

  const handleReset = async (c: CaseListItem) => {
    if (!token) return;
    setResetting(true);
    try {
      await apiFetch(`/practice/${c.id}/reset`, { method: "POST", token });
      // Refresh practice sessions
      const updated = await apiFetch<PracticeSessionInfo[]>("/practice/my", { token });
      setPracticeSessions(updated);
      // Also reset assignment status back to pending
      const assignment = assignmentByCase.get(c.id);
      if (assignment) {
        await apiFetch(`/assignments/${assignment.id}`, {
          method: "PATCH",
          body: { status: "pending" },
          token,
        }).catch(() => {});
        const updatedAssignments = await apiFetch<Assignment[]>("/assignments/my", { token });
        setAssignments(updatedAssignments);
      }
    } catch {
      // silently fail
    } finally {
      setResetting(false);
      setResetDialogCase(null);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return null;
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const isOverdue = (dueDate: string | null) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  const getPracticeStatus = (caseId: string): "not_started" | "in_progress" | "submitted" => {
    const session = practiceByCase.get(caseId);
    return session?.status || "not_started";
  };

  const getButtonLabel = (caseId: string): string => {
    const practiceStatus = getPracticeStatus(caseId);
    switch (practiceStatus) {
      case "submitted":
        return "Completed";
      case "in_progress":
        return "Resume";
      default:
        return "Start practice";
    }
  };

  const getButtonColor = (caseId: string): "primary" | "success" | "info" => {
    const practiceStatus = getPracticeStatus(caseId);
    switch (practiceStatus) {
      case "submitted":
        return "success";
      case "in_progress":
        return "info";
      default:
        return "primary";
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <PageTitle>Practice cases</PageTitle>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Select a case to begin your virtual patient encounter
        </Typography>
      </Box>

      {isLoading ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : assignedCases.length === 0 ? (
        <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
          <ClipboardList size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No cases available
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Your instructor hasn't assigned any cases yet. Check back later.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {assignedCases.map((c) => {
            const avatarUrl = c.avatar_url || null;
            const assignment = assignmentByCase.get(c.id)!;
            const overdue = isOverdue(assignment.due_date) && assignment.status !== "completed";
            const practiceStatus = getPracticeStatus(c.id);
            const isSubmitted = practiceStatus === "submitted";
            return (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={c.id}>
                <Card
                  sx={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    borderRadius: 2,
                    border: overdue ? 2 : 0,
                    borderColor: overdue ? "error.main" : undefined,
                    transition: "box-shadow 0.2s, transform 0.15s",
                    "&:hover": {
                      boxShadow: 4,
                      transform: "translateY(-2px)",
                    },
                  }}
                >
                  <Box
                    onClick={() => handleStartPractice(c)}
                    sx={{ cursor: "pointer" }}
                  >
                    {avatarUrl ? (
                      <CardMedia
                        component="img"
                        image={avatarUrl}
                        alt={c.patient_name || c.title}
                        sx={{ height: 220, objectFit: "cover", objectPosition: "center 20%" }}
                      />
                    ) : (
                      <Box
                        sx={{
                          height: 220,
                          bgcolor: "action.hover",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <MessageSquare size={40} style={{ opacity: 0.15 }} />
                      </Box>
                    )}
                  </Box>

                  <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 0.5 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                      <Chip
                        size="small"
                        label={
                          practiceStatus === "submitted"
                            ? "Completed"
                            : practiceStatus === "in_progress"
                            ? "In progress"
                            : "Not started"
                        }
                        color={
                          practiceStatus === "submitted"
                            ? "success"
                            : practiceStatus === "in_progress"
                            ? "info"
                            : "default"
                        }
                        sx={{ height: 22, textTransform: "capitalize" }}
                      />
                      {assignment.due_date && (
                        <Chip
                          size="small"
                          icon={<Calendar size={12} />}
                          label={`Due ${formatDate(assignment.due_date)}`}
                          color={overdue ? "error" : "default"}
                          variant="outlined"
                          sx={{ height: 22 }}
                        />
                      )}
                    </Box>

                    <Typography variant="h6" fontWeight={500}>
                      {c.title}
                    </Typography>

                    {c.patient_name && (
                      <SmallText>Patient: {c.patient_name}</SmallText>
                    )}

                    {c.description && (
                      <SmallText sx={{ color: "text.secondary", flex: 1 }}>
                        {c.description}
                      </SmallText>
                    )}

                    <Box sx={{ pt: 1.5, display: "flex", gap: 1, alignItems: "center" }}>
                      <Box sx={{ flex: 1 }}>
                        {isSubmitted ? (
                          <SecondaryButton
                            size="small"
                            fullWidth
                            onClick={() => handleStartPractice(c)}
                            color="success"
                          >
                            Completed
                          </SecondaryButton>
                        ) : (
                          <PrimaryButton
                            size="small"
                            fullWidth
                            onClick={() => handleStartPractice(c)}
                          >
                            {getButtonLabel(c.id)}
                          </PrimaryButton>
                        )}
                      </Box>
                      {/* Reset button — only show if session has started */}
                      {practiceStatus !== "not_started" && (
                        <Tooltip title="Reset case — start over">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              setResetDialogCase(c);
                            }}
                            sx={{
                              border: 1,
                              borderColor: "divider",
                              borderRadius: 1.5,
                              p: 0.8,
                            }}
                          >
                            <RotateCcw size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      {/* Reset confirmation dialog */}
      <Dialog
        open={!!resetDialogCase}
        onClose={() => !resetting && setResetDialogCase(null)}
      >
        <DialogTitle>Reset case?</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            This will clear your entire conversation history for{" "}
            <strong>{resetDialogCase?.title}</strong> and start over from scratch.
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogCase(null)} disabled={resetting}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => resetDialogCase && handleReset(resetDialogCase)}
            disabled={resetting}
          >
            {resetting ? "Resetting..." : "Reset"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
