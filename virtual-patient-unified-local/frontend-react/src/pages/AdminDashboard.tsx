import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Avatar from "@mui/material/Avatar";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardActions from "@mui/material/CardActions";
import CardMedia from "@mui/material/CardMedia";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import {
  Plus, Edit3, Trash2, Eye, EyeOff, ClipboardList, MessageSquare,
  LayoutGrid, List,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useCaseStore, CaseListItem, CaseDetail, CaseCreatePayload } from "../stores/caseStore";
import { apiFetch } from "../api/client";
import {
  PageTitle, PrimaryButton, DangerButton, FlexBetween, StatusChip,
} from "../components/styled";
import CaseFormDialog from "../components/CaseFormDialog";
import ImageLibrary from "../components/ImageLibrary";
import Assignments from "../components/Assignments";
import Transcripts from "../components/Transcripts";
import GlobalPrompt from "../components/GlobalPrompt";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const { cases, isLoading, fetchCases, createCase, updateCase, deleteCase, publishCase, unpublishCase } = useCaseStore();

  const [tabIndex, setTabIndex] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCase, setEditingCase] = useState<
    (CaseListItem & { system_prompt?: string; voice_id?: string; avatar_filename?: string | null }) | undefined
  >();
  const [deleteDialog, setDeleteDialog] = useState<CaseListItem | null>(null);
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  useEffect(() => {
    if (token) fetchCases(token);
  }, [token]);

  const showSnack = (message: string, severity: "success" | "error" = "success") => {
    setSnack({ message, severity });
  };

  const handleCreate = async (data: CaseCreatePayload, avatarFile?: File) => {
    if (token) {
      await createCase(token, data, avatarFile);
      showSnack(`Case "${data.title}" created`);
    }
  };

  const handleEdit = async (caseItem: CaseListItem) => {
    if (!token) return;
    try {
      const detail = await apiFetch<CaseDetail>(`/cases/${caseItem.id}`, { token });
      setEditingCase({
        ...caseItem,
        system_prompt: detail.system_prompt,
        voice_id: detail.voice_id ?? undefined,
        avatar_filename: detail.avatar_filename,
      });
      setFormOpen(true);
    } catch (err: any) {
      showSnack(err.message || "Failed to load case details", "error");
    }
  };

  const handleUpdate = async (data: CaseCreatePayload, avatarFile?: File) => {
    if (token && editingCase) {
      await updateCase(token, editingCase.id, data, avatarFile);
      showSnack(`Case "${data.title}" updated`);
    }
  };

  const handleDelete = async () => {
    if (token && deleteDialog) {
      const title = deleteDialog.title;
      await deleteCase(token, deleteDialog.id);
      setDeleteDialog(null);
      showSnack(`Case "${title}" deleted`);
    }
  };

  const handleTogglePublish = async (c: CaseListItem) => {
    if (!token) return;
    if (c.status === "draft") {
      await publishCase(token, c.id);
      showSnack(`"${c.title}" published`);
    } else {
      await unpublishCase(token, c.id);
      showSnack(`"${c.title}" moved back to draft`);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <Box>
      <Tabs
        value={tabIndex}
        onChange={(_, v) => setTabIndex(v)}
        sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Cases" />
        <Tab label="Global Prompt" />
        <Tab label="Assignments" />
        <Tab label="Transcripts" />
        <Tab label="Image Library" />
      </Tabs>

      {tabIndex === 0 && (
        <Box>
          <FlexBetween sx={{ mb: 3 }}>
            <Box>
              <PageTitle>Cases</PageTitle>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Manage virtual patient scenarios for student practice
              </Typography>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {/* View toggle */}
              <Box
                sx={{
                  display: "flex",
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  overflow: "hidden",
                }}
              >
                <IconButton
                  size="small"
                  onClick={() => setViewMode("grid")}
                  sx={{
                    borderRadius: 0,
                    bgcolor: viewMode === "grid" ? "action.selected" : "transparent",
                    px: 1,
                  }}
                >
                  <LayoutGrid size={16} />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => setViewMode("list")}
                  sx={{
                    borderRadius: 0,
                    bgcolor: viewMode === "list" ? "action.selected" : "transparent",
                    px: 1,
                  }}
                >
                  <List size={16} />
                </IconButton>
              </Box>
              <PrimaryButton
                startIcon={<Plus size={16} />}
                onClick={() => { setEditingCase(undefined); setFormOpen(true); }}
              >
                New case
              </PrimaryButton>
            </Box>
          </FlexBetween>

          {isLoading ? (
            <Box sx={{ textAlign: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : cases.length === 0 ? (
            <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
              <ClipboardList size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No cases yet
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Create your first virtual patient case for students to practice with.
              </Typography>
              <PrimaryButton
                startIcon={<Plus size={16} />}
                onClick={() => { setEditingCase(undefined); setFormOpen(true); }}
              >
                Create first case
              </PrimaryButton>
            </Paper>
          ) : viewMode === "grid" ? (
            /* ── Grid / Card view ── */
            <Grid container spacing={2.5}>
              {cases.map((c) => {
                const avatarUrl = c.avatar_url || null;
                return (
                  <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={c.id}>
                    <Card
                      sx={{
                        height: "100%",
                        display: "flex",
                        flexDirection: "column",
                        borderRadius: 2,
                        cursor: "pointer",
                        transition: "box-shadow 0.2s, transform 0.15s",
                        "&:hover": {
                          boxShadow: 4,
                          transform: "translateY(-2px)",
                        },
                      }}
                      onClick={() => navigate(`/admin/practice/${c.id}`)}
                    >
                      {/* Thumbnail */}
                      {avatarUrl ? (
                        <CardMedia
                          component="img"
                          image={avatarUrl}
                          alt={c.patient_name || c.title}
                          sx={{
                            height: 220,
                            objectFit: "cover",
                            objectPosition: "center 20%",
                          }}
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

                      <CardContent sx={{ flex: 1, pb: 0 }}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                          <StatusChip status={c.status} />
                        </Box>
                        <Typography variant="subtitle2" fontWeight={600} noWrap>
                          {c.title}
                        </Typography>
                        {c.patient_name && (
                          <Typography variant="caption" color="text.secondary">
                            {c.patient_name}
                          </Typography>
                        )}
                        {c.description && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                              overflow: "hidden",
                              mt: 0.5,
                            }}
                          >
                            {c.description}
                          </Typography>
                        )}
                      </CardContent>

                      <CardActions sx={{ px: 2, pb: 1.5, pt: 0.5 }} onClick={(e) => e.stopPropagation()}>
                        <Tooltip title={c.status === "draft" ? "Publish" : "Unpublish"}>
                          <IconButton size="small" onClick={() => handleTogglePublish(c)}>
                            {c.status === "draft" ? <Eye size={15} /> : <EyeOff size={15} />}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit">
                          <IconButton size="small" onClick={() => handleEdit(c)}>
                            <Edit3 size={15} />
                          </IconButton>
                        </Tooltip>
                        <Box sx={{ flex: 1 }} />
                        <Tooltip title="Delete">
                          <IconButton size="small" onClick={() => setDeleteDialog(c)} color="error">
                            <Trash2 size={15} />
                          </IconButton>
                        </Tooltip>
                      </CardActions>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          ) : (
            /* ── List / Table view ── */
            <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, width: 64 }}></TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Title</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Patient</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Updated</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cases.map((c) => {
                    const avatarUrl = c.avatar_url || null;
                    return (
                      <TableRow
                        key={c.id}
                        hover
                        onClick={() => navigate(`/admin/practice/${c.id}`)}
                        sx={{
                          cursor: "pointer",
                          "&:hover": { bgcolor: (t) => `${t.palette.secondary.main}0A` },
                        }}
                      >
                        <TableCell sx={{ pr: 0 }}>
                          {avatarUrl ? (
                            <Avatar
                              variant="rounded"
                              src={avatarUrl}
                              sx={{
                                width: 44,
                                height: 44,
                                "& img": { objectPosition: "center 20%" },
                              }}
                            />
                          ) : (
                            <Avatar variant="rounded" sx={{ width: 44, height: 44, bgcolor: "action.hover" }}>
                              <MessageSquare size={18} style={{ opacity: 0.4 }} />
                            </Avatar>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={500}>{c.title}</Typography>
                          {c.description && (
                            <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 300, display: "block" }}>
                              {c.description}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>{c.patient_name || "—"}</TableCell>
                        <TableCell>
                          <StatusChip status={c.status} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(c.updated_at)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                          <Tooltip title={c.status === "draft" ? "Publish" : "Unpublish"}>
                            <IconButton size="small" onClick={() => handleTogglePublish(c)}>
                              {c.status === "draft" ? <Eye size={16} /> : <EyeOff size={16} />}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit">
                            <IconButton size="small" onClick={() => handleEdit(c)}>
                              <Edit3 size={16} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete">
                            <IconButton size="small" onClick={() => setDeleteDialog(c)} color="error">
                              <Trash2 size={16} />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}

      {tabIndex === 1 && <GlobalPrompt />}

      {tabIndex === 2 && <Assignments />}

      {tabIndex === 3 && <Transcripts />}

      {tabIndex === 4 && <ImageLibrary />}

      <CaseFormDialog
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingCase(undefined); }}
        onSubmit={editingCase ? handleUpdate : handleCreate}
        editCase={editingCase}
      />

      <Dialog open={!!deleteDialog} onClose={() => setDeleteDialog(null)}>
        <DialogTitle>Delete case</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{deleteDialog?.title}"? This cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteDialog(null)}>Cancel</Button>
          <DangerButton onClick={handleDelete}>Delete</DangerButton>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setSnack(null)}
          severity={snack?.severity || "success"}
          variant="filled"
          sx={{ borderRadius: 1 }}
        >
          {snack?.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
