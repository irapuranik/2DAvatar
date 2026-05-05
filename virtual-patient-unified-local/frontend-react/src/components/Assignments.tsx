import { useEffect, useState, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Avatar from "@mui/material/Avatar";
import { X, Calendar, Trash2, UserPlus, MessageSquare, Check } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";
import { CaseListItem } from "../stores/caseStore";
import { PrimaryButton, SmallText } from "./styled";

interface Assignment {
  id: string;
  student_id: string;
  case_id: string;
  assigned_by: string;
  due_date: string | null;
  status: "pending" | "in_progress" | "completed";
  completed_at: string | null;
  created_at: string;
  student_email: string | null;
  student_name: string | null;
  case_title: string | null;
}

interface StudentInfo {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

export default function Assignments() {
  const { token } = useAuthStore();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [students, setStudents] = useState<StudentInfo[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [selectedStudents, setSelectedStudents] = useState<Set<string>>(new Set());
  const [dueDateDialog, setDueDateDialog] = useState(false);
  const [dueDate, setDueDate] = useState("");
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);
  const [filterUnassigned, setFilterUnassigned] = useState(false);

  const fetchAll = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [casesData, studentsData, assignmentsData] = await Promise.all([
        apiFetch<CaseListItem[]>("/cases", { token }),
        apiFetch<StudentInfo[]>("/auth/users", { token }),
        apiFetch<Assignment[]>("/assignments", { token }),
      ]);
      setCases(casesData.filter((c) => c.status === "published"));
      setStudents(studentsData.filter((s) => s.role === "student" && s.is_active));
      setAssignments(assignmentsData);
    } catch (err: any) {
      setSnack({ message: err.message || "Failed to load data", severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Get assignments for the selected case
  const caseAssignments = selectedCase
    ? assignments.filter((a) => a.case_id === selectedCase.id)
    : [];

  const assignedStudentIds = new Set(caseAssignments.map((a) => a.student_id));

  // Filter students based on toggle
  const displayStudents = filterUnassigned
    ? students.filter((s) => !assignedStudentIds.has(s.id))
    : students;

  const toggleStudent = (id: string) => {
    setSelectedStudents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllStudents = () => {
    const unassigned = displayStudents.filter((s) => !assignedStudentIds.has(s.id));
    if (selectedStudents.size === unassigned.length) {
      setSelectedStudents(new Set());
    } else {
      setSelectedStudents(new Set(unassigned.map((s) => s.id)));
    }
  };

  const handleAssign = async () => {
    if (!token || !selectedCase || selectedStudents.size === 0) return;
    setAssigning(true);
    try {
      const body = Array.from(selectedStudents).map((studentId) => ({
        student_id: studentId,
        case_id: selectedCase.id,
        due_date: dueDate || null,
      }));
      await apiFetch("/assignments/bulk", { method: "POST", body, token });
      setSnack({ message: `Assigned ${selectedStudents.size} student(s) to "${selectedCase.title}"`, severity: "success" });
      setSelectedStudents(new Set());
      setDueDate("");
      setDueDateDialog(false);
      await fetchAll();
    } catch (err: any) {
      setSnack({ message: err.message || "Assignment failed", severity: "error" });
    } finally {
      setAssigning(false);
    }
  };

  const handleUnassign = async (assignmentId: string) => {
    if (!token) return;
    try {
      await apiFetch(`/assignments/${assignmentId}`, { method: "DELETE", token });
      setSnack({ message: "Assignment removed", severity: "success" });
      await fetchAll();
    } catch (err: any) {
      setSnack({ message: err.message || "Failed to remove", severity: "error" });
    }
  };

  const handleStatusToggle = async (assignment: Assignment) => {
    if (!token) return;
    const newStatus = assignment.status === "completed" ? "pending" : "completed";
    try {
      await apiFetch(`/assignments/${assignment.id}`, {
        method: "PATCH",
        body: { status: newStatus },
        token,
      });
      await fetchAll();
    } catch (err: any) {
      setSnack({ message: err.message || "Failed to update", severity: "error" });
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return null;
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  if (loading) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const completedCount = selectedCase
    ? caseAssignments.filter((a) => a.status === "completed").length
    : 0;

  return (
    <Box sx={{ display: "flex", gap: 3, minHeight: 500 }}>
      {/* ── Left panel: Cases list ── */}
      <Paper
        sx={{
          width: 340,
          flexShrink: 0,
          borderRadius: 2,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle2" fontWeight={700} textTransform="uppercase" color="text.secondary" fontSize="0.7rem">
            Available Cases
          </Typography>
          <SmallText>{cases.length} case(s)</SmallText>
        </Box>
        <Box sx={{ flex: 1, overflow: "auto" }}>
          {cases.map((c) => {
            const isSelected = selectedCase?.id === c.id;
            const caseAssignCount = assignments.filter((a) => a.case_id === c.id).length;
            return (
              <Box
                key={c.id}
                onClick={() => {
                  setSelectedCase(c);
                  setSelectedStudents(new Set());
                }}
                sx={{
                  px: 2,
                  py: 1.5,
                  cursor: "pointer",
                  borderBottom: 1,
                  borderColor: "divider",
                  bgcolor: isSelected ? "primary.main" : "transparent",
                  color: isSelected ? "primary.contrastText" : "text.primary",
                  "&:hover": {
                    bgcolor: isSelected ? "primary.main" : "action.hover",
                  },
                  transition: "background 0.15s",
                }}
              >
                <Typography variant="body2" fontWeight={600} noWrap>
                  {c.title}
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.3 }}>
                  {c.patient_name && (
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>
                      {c.patient_name}
                    </Typography>
                  )}
                  <Chip
                    size="small"
                    label={`${caseAssignCount} assigned`}
                    sx={{
                      height: 18,
                      fontSize: "0.65rem",
                      bgcolor: isSelected ? "rgba(255,255,255,0.2)" : undefined,
                    }}
                  />
                </Box>
              </Box>
            );
          })}
        </Box>
      </Paper>

      {/* ── Right panel: Students + Assignments ── */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
        {!selectedCase ? (
          <Paper sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 2 }}>
            <Box sx={{ textAlign: "center", py: 6 }}>
              <MessageSquare size={48} style={{ opacity: 0.15, marginBottom: 16 }} />
              <Typography variant="h6" color="text.secondary">
                Select a case
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Choose a case from the left to manage student assignments
              </Typography>
            </Box>
          </Paper>
        ) : (
          <>
            {/* Case header */}
            <Paper sx={{ px: 2.5, py: 2, borderRadius: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Typography variant="h6" fontWeight={600}>
                    {selectedCase.title}
                  </Typography>
                  {selectedCase.patient_name && (
                    <SmallText>Patient: {selectedCase.patient_name}</SmallText>
                  )}
                </Box>
                <Chip
                  label={`${completedCount}/${caseAssignments.length} Complete`}
                  color={completedCount === caseAssignments.length && caseAssignments.length > 0 ? "success" : "default"}
                  size="small"
                  variant="outlined"
                />
              </Box>
            </Paper>

            {/* Assigned students */}
            {caseAssignments.length > 0 && (
              <Paper sx={{ px: 2.5, py: 2, borderRadius: 2 }}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
                  Assigned Students ({caseAssignments.length})
                </Typography>
                {caseAssignments.map((a) => (
                  <Box
                    key={a.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      py: 1,
                      borderBottom: 1,
                      borderColor: "divider",
                      "&:last-child": { borderBottom: 0 },
                    }}
                  >
                    <Avatar sx={{ width: 32, height: 32, fontSize: "0.8rem", bgcolor: "secondary.main" }}>
                      {(a.student_name || a.student_email || "S")[0].toUpperCase()}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={500}>
                        {a.student_name || a.student_email}
                      </Typography>
                      {a.due_date && (
                        <Typography variant="caption" color="text.secondary">
                          Due: {formatDate(a.due_date)}
                        </Typography>
                      )}
                    </Box>
                    <Chip
                      size="small"
                      label={a.status.replace("_", " ")}
                      color={a.status === "completed" ? "success" : a.status === "in_progress" ? "info" : "default"}
                      onClick={() => handleStatusToggle(a)}
                      sx={{ cursor: "pointer", textTransform: "capitalize", height: 24 }}
                    />
                    <Tooltip title="Remove assignment">
                      <IconButton size="small" onClick={() => handleUnassign(a.id)} color="error">
                        <Trash2 size={14} />
                      </IconButton>
                    </Tooltip>
                  </Box>
                ))}
              </Paper>
            )}

            {/* Student selection for new assignment */}
            <Paper sx={{ px: 2.5, py: 2, borderRadius: 2, flex: 1 }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
                <Typography variant="subtitle2" fontWeight={600}>
                  Assign Students
                </Typography>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Chip
                    label="All Students"
                    size="small"
                    variant={!filterUnassigned ? "filled" : "outlined"}
                    onClick={() => setFilterUnassigned(false)}
                    sx={{ cursor: "pointer" }}
                  />
                  <Chip
                    label="Unassigned Only"
                    size="small"
                    variant={filterUnassigned ? "filled" : "outlined"}
                    onClick={() => setFilterUnassigned(true)}
                    sx={{ cursor: "pointer" }}
                  />
                </Box>
              </Box>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {selectedStudents.size} of {displayStudents.filter((s) => !assignedStudentIds.has(s.id)).length} selected
                </Typography>
                <Button size="small" onClick={selectAllStudents} sx={{ fontSize: "0.7rem", minWidth: 0 }}>
                  {selectedStudents.size === displayStudents.filter((s) => !assignedStudentIds.has(s.id)).length
                    ? "Deselect All"
                    : "Select All"}
                </Button>
              </Box>

              <Box sx={{ maxHeight: 300, overflow: "auto" }}>
                {displayStudents.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                    {filterUnassigned ? "All students have been assigned this case" : "No students found"}
                  </Typography>
                ) : (
                  displayStudents.map((s) => {
                    const isAssigned = assignedStudentIds.has(s.id);
                    return (
                      <Box
                        key={s.id}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          py: 0.8,
                          px: 1,
                          borderRadius: 1,
                          opacity: isAssigned ? 0.5 : 1,
                          "&:hover": { bgcolor: isAssigned ? "transparent" : "action.hover" },
                        }}
                      >
                        <Checkbox
                          size="small"
                          checked={selectedStudents.has(s.id)}
                          disabled={isAssigned}
                          onChange={() => toggleStudent(s.id)}
                        />
                        <Avatar sx={{ width: 28, height: 28, fontSize: "0.7rem", bgcolor: "secondary.main" }}>
                          {s.display_name[0].toUpperCase()}
                        </Avatar>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="body2" fontWeight={500}>
                            {s.display_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {s.email}
                          </Typography>
                        </Box>
                        {isAssigned && (
                          <Chip size="small" label="Assigned" sx={{ height: 20, fontSize: "0.6rem" }} />
                        )}
                      </Box>
                    );
                  })
                )}
              </Box>

              {selectedStudents.size > 0 && (
                <Box sx={{ display: "flex", gap: 1, mt: 2, pt: 2, borderTop: 1, borderColor: "divider" }}>
                  <PrimaryButton
                    startIcon={<UserPlus size={14} />}
                    onClick={() => setDueDateDialog(true)}
                    disabled={assigning}
                    size="small"
                  >
                    Assign {selectedStudents.size} Student(s)
                  </PrimaryButton>
                </Box>
              )}
            </Paper>
          </>
        )}
      </Box>

      {/* Due date dialog */}
      <Dialog open={dueDateDialog} onClose={() => setDueDateDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Set Due Date (Optional)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Optionally set a due date for this assignment. Leave blank for no deadline.
          </Typography>
          <TextField
            type="date"
            fullWidth
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            label="Due Date"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setDueDateDialog(false); setDueDate(""); }}>Cancel</Button>
          <PrimaryButton onClick={handleAssign} disabled={assigning}>
            {assigning ? <CircularProgress size={16} /> : "Assign"}
          </PrimaryButton>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert onClose={() => setSnack(null)} severity={snack?.severity || "success"} variant="filled">
          {snack?.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
