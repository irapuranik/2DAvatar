import { useState, useEffect, useRef } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import MenuItem from "@mui/material/MenuItem";
import Link from "@mui/material/Link";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { Image as ImageIcon, X, Copy } from "lucide-react";
import { PrimaryButton } from "./styled";
import { CaseCreatePayload, CaseListItem, CaseDetail, useCaseStore } from "../stores/caseStore";
import { apiFetch, BACKEND_URL } from "../api/client";
import { useAuthStore } from "../stores/authStore";
import AvatarPickerDialog, { AvatarSelection } from "./AvatarPickerDialog";

interface CaseFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CaseCreatePayload, avatarFile?: File) => Promise<void>;
  editCase?: CaseListItem & {
    system_prompt?: string;
    voice_id?: string;
    avatar_filename?: string | null;
    viseme_shapes_base_url?: string | null;
  };
}

interface VisemeJobStatus {
  job_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  case_id?: string | null;
  current_viseme?: string | null;
  progress?: string | null;
  written?: string[] | null;
  diagnostics?: Record<string, unknown> | null;
  error?: string | null;
}

// Kept for future use — currently commented out in the UI
const _SCENARIO_TYPES = [
  { value: "custom", label: "Custom" },
  { value: "angry-parent", label: "Angry parent" },
  { value: "anxious-patient", label: "Anxious patient" },
  { value: "rude-patient", label: "Rude patient" },
  { value: "grief-counseling", label: "Grief counseling" },
  { value: "pediatric-consult", label: "Pediatric consult" },
];
void _SCENARIO_TYPES; // suppress unused warning

const VOICE_PRESETS = [
  { value: "Cz0K1kOv9tD8l0b5Qu53", label: "Male, American, Natural" },
  { value: "NOpBlnGInO9m6vDvFkFC", label: "Old Male, American, Relaxed" },
  { value: "e0M6Qv9xPZbhXjsTsy8J", label: "Female, American, Natural" },
  { value: "5u41aNhyCU6hXOcjPPv0", label: "Old Female, American, Relaxed" },
  { value: "__custom__", label: "Custom voice ID" },
];

export default function CaseFormDialog({ open, onClose, onSubmit, editCase }: CaseFormDialogProps) {
  const { token } = useAuthStore();
  const { cases } = useCaseStore();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [patientName, setPatientName] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [voicePreset, setVoicePreset] = useState("");
  const [scenarioType, setScenarioType] = useState("custom");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  // Avatar state
  const [avatarFile, setAvatarFile] = useState<File | undefined>();
  const [selectedLibraryFile, setSelectedLibraryFile] = useState<string | null>(null);
  const [avatarPreviewUrl, setAvatarPreviewUrl] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const visemeFileRef = useRef<HTMLInputElement>(null);
  const [visemePrompt, setVisemePrompt] = useState("");
  const [visemeHint, setVisemeHint] = useState("");
  const [visemeJobId, setVisemeJobId] = useState<string | null>(null);
  const [visemeStatusLine, setVisemeStatusLine] = useState("");
  const [visemeUploading, setVisemeUploading] = useState(false);
  const [generateBaseFromPrompt, setGenerateBaseFromPrompt] = useState(false);

  const handleUseTemplate = async (caseId: string) => {
    if (!token || !caseId) return;
    setLoadingTemplate(true);
    try {
      const detail = await apiFetch<CaseDetail>(`/cases/${caseId}`, { token });
      setTitle(detail.title + " (Copy)");
      setDescription(detail.description || "");
      setSystemPrompt(detail.system_prompt || "");
      setPatientName(detail.patient_name || "");
      setScenarioType(detail.scenario_type || "custom");
      // Set voice
      const vid = detail.voice_id || "";
      const matchedPreset = VOICE_PRESETS.find((p) => p.value === vid);
      if (vid && !matchedPreset) {
        setVoicePreset("__custom__");
        setVoiceId(vid);
      } else {
        setVoicePreset(vid);
        setVoiceId("");
      }
      // Set avatar if the template has one
      if (detail.avatar_filename) {
        setSelectedLibraryFile(detail.avatar_filename);
        setAvatarPreviewUrl(detail.avatar_url || null);
      }
    } catch {
      setError("Failed to load template case");
    } finally {
      setLoadingTemplate(false);
    }
  };

  // When the dialog is closed, clear which case we last reset visemes for (fresh viseme row on next open).
  const lastVisemeCaseKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open) {
      lastVisemeCaseKeyRef.current = null;
      return;
    }
    if (editCase) {
      setTitle(editCase.title);
      setDescription(editCase.description || "");
      setSystemPrompt(editCase.system_prompt || "");
      setPatientName(editCase.patient_name || "");
      const vid = editCase.voice_id || "";
      const matchedPreset = VOICE_PRESETS.find((p) => p.value === vid);
      if (vid && !matchedPreset) {
        setVoicePreset("__custom__");
        setVoiceId(vid);
      } else {
        setVoicePreset(vid);
        setVoiceId("");
      }
      setScenarioType(editCase.scenario_type);
      setSelectedLibraryFile(editCase.avatar_filename || null);
      setAvatarPreviewUrl(editCase.avatar_url || null);
    } else {
      setTitle("");
      setDescription("");
      setSystemPrompt("");
      setPatientName("");
      setVoiceId("");
      setVoicePreset("");
      setScenarioType("custom");
      setSelectedLibraryFile(null);
      setAvatarPreviewUrl(null);
    }
    setAvatarFile(undefined);
    setError("");
  }, [open, editCase]);

  // Reset viseme fields only when opening the dialog or switching to a different case — not when `editCase`
  // gets a new object reference for the same row (that was clearing the "generate from prompt" checkbox).
  useEffect(() => {
    if (!open) return;
    const caseKey = editCase?.id ?? "__create__";
    if (lastVisemeCaseKeyRef.current === caseKey) return;
    lastVisemeCaseKeyRef.current = caseKey;
    setVisemePrompt("");
    setVisemeHint("");
    setVisemeJobId(null);
    setVisemeStatusLine("");
    setVisemeUploading(false);
    setGenerateBaseFromPrompt(false);
  }, [open, editCase?.id]);

  useEffect(() => {
    if (!visemeJobId || !token) return;
    const id = visemeJobId;
    const tick = async () => {
      try {
        const st = await apiFetch<VisemeJobStatus>(`/admin/visemes/jobs/${id}`, { token });
        const diag = (st.diagnostics || {}) as {
          visemes?: Record<string, { retry_count?: number; status?: string }>;
        };
        const retryTotal = Object.values(diag.visemes || {}).reduce((sum, v) => sum + (v?.retry_count || 0), 0);
        const line =
          st.status === "running"
            ? `Generating… ${st.current_viseme ?? ""} ${st.progress ?? ""}`.trim()
            : st.status === "queued"
              ? "Queued…"
              : "";
        setVisemeStatusLine(line);
        if (st.status === "completed") {
          setVisemeJobId(null);
          setVisemeStatusLine(
            `Done. Wrote ${(st.written || []).join(", ")}. Retries used: ${retryTotal}. Re-open this case or refresh the list, then open practice.`,
          );
        }
        if (st.status === "failed") {
          setVisemeJobId(null);
          setVisemeStatusLine(st.error || "Generation failed");
        }
      } catch {
        setVisemeJobId(null);
        setVisemeStatusLine("Failed to poll job status");
      }
    };
    tick();
    const interval = window.setInterval(tick, 2500);
    return () => window.clearInterval(interval);
  }, [visemeJobId, token]);

  const uploadVisemeReference = async (file: File) => {
    if (!token || !editCase?.id) return;
    setVisemeUploading(true);
    setVisemeStatusLine("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BACKEND_URL}/api/cases/${editCase.id}/viseme-reference`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      setVisemeStatusLine("Reference A.png uploaded. You can run Generate visemes.");
    } catch (e: unknown) {
      setVisemeStatusLine(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setVisemeUploading(false);
    }
  };

  const startVisemeGeneration = async () => {
    if (!token || !editCase?.id) return;
    if (generateBaseFromPrompt && !visemePrompt.trim() && !visemeHint.trim()) {
      setVisemeStatusLine("Fill Prompt or Extra hint when generating the base face from text.");
      return;
    }
    setVisemeStatusLine("");
    try {
      const res = await apiFetch<{ job_id: string; message: string }>("/admin/visemes/generate-for-case", {
        method: "POST",
        token,
        body: {
          case_id: editCase.id,
          prompt: visemePrompt.trim(),
          character_hint: visemeHint.trim(),
          generate_base_face_from_prompt: generateBaseFromPrompt,
        },
      });
      setVisemeJobId(res.job_id);
      setVisemeStatusLine("Job started…");
    } catch (e: unknown) {
      setVisemeStatusLine(e instanceof Error ? e.message : "Failed to start");
    }
  };

  const handleAvatarSelect = (selection: AvatarSelection) => {
    if (selection.type === "library") {
      setSelectedLibraryFile(selection.filename!);
      setAvatarFile(undefined);
    } else {
      setAvatarFile(selection.file);
      setSelectedLibraryFile(null);
    }
    setAvatarPreviewUrl(selection.previewUrl);
  };

  const handleAvatarRemove = () => {
    setAvatarFile(undefined);
    setSelectedLibraryFile(null);
    setAvatarPreviewUrl(null);
  };

  const hasAvatar = !!(selectedLibraryFile || avatarFile);

  // Resolve the actual voice ID from preset or custom input
  const resolvedVoiceId =
    voicePreset === "__custom__"
      ? voiceId.trim()
      : voicePreset || undefined;

  const handleSubmit = async () => {
    if (!title.trim() || !systemPrompt.trim()) {
      setError("Title and system prompt are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSubmit(
        {
          title: title.trim(),
          description: description.trim() || undefined,
          system_prompt: systemPrompt.trim(),
          patient_name: patientName.trim() || undefined,
          has_avatar: hasAvatar,
          avatar_filename: selectedLibraryFile || undefined,
          voice_id: resolvedVoiceId || undefined,
          scenario_type: scenarioType,
        },
        avatarFile,
      );
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save case");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>
          {editCase ? "Edit case" : "Create new case"}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "8px !important" }}>
          {error && <Alert severity="error" sx={{ borderRadius: 1 }}>{error}</Alert>}

          {/* Preset / template selector — only shown when creating a new case */}
          {!editCase && cases.length > 0 && (
            <Box>
              <TextField
                label="Use existing case as template"
                fullWidth
                select
                value=""
                onChange={(e) => handleUseTemplate(e.target.value)}
                disabled={loadingTemplate}
                size="small"
                helperText="Optional: pre-fill fields from an existing case"
              >
                <MenuItem value="">
                  <em>Start from scratch</em>
                </MenuItem>
                {cases.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Copy size={14} style={{ opacity: 0.5 }} />
                      {c.title}
                      {c.patient_name && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                          ({c.patient_name})
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                ))}
              </TextField>
              <Divider sx={{ mt: 1 }} />
            </Box>
          )}

          {/* Row 1: Title */}
          <TextField
            label="Case title"
            fullWidth
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
            required
          />

          {/* Row 2: Patient name */}
          <TextField
            label="Patient name"
            fullWidth
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            placeholder="e.g. Maria Santos"
          />

          {/* Row 3: Voice selection */}
          <Box>
            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
              <TextField
                label="Voice"
                fullWidth
                select
                value={voicePreset}
                onChange={(e) => {
                  setVoicePreset(e.target.value);
                  if (e.target.value !== "__custom__") setVoiceId("");
                }}
              >
                <MenuItem value="">
                  <em>Default voice</em>
                </MenuItem>
                {VOICE_PRESETS.map((v) => (
                  <MenuItem key={v.value} value={v.value}>
                    {v.label}
                  </MenuItem>
                ))}
              </TextField>
              {voicePreset === "__custom__" && (
                <TextField
                  label="Voice ID"
                  fullWidth
                  value={voiceId}
                  onChange={(e) => setVoiceId(e.target.value)}
                  placeholder="Paste ElevenLabs Voice ID"
                />
              )}
            </Box>
            <Link
              href="https://elevenlabs.io/app/voice-library"
              target="_blank"
              rel="noopener"
              variant="caption"
              color="text.secondary"
              sx={{ mt: 0.5, display: "inline-block", fontSize: "0.7rem" }}
            >
              Browse voice library →
            </Link>
          </Box>

          {/* Row 4: Description */}
          <TextField
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of the scenario for students..."
          />

          {/* Row 5: Patient picture — inline button/preview */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            {avatarPreviewUrl ? (
              <>
                <Box
                  sx={{
                    position: "relative",
                    width: 56,
                    height: 56,
                    flexShrink: 0,
                    borderRadius: 1.5,
                    overflow: "hidden",
                    border: 1,
                    borderColor: "divider",
                  }}
                >
                  <Box
                    component="img"
                    src={avatarPreviewUrl}
                    sx={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      objectPosition: "top",
                      display: "block",
                    }}
                  />
                  <Box
                    onClick={handleAvatarRemove}
                    sx={{
                      position: "absolute",
                      top: 2,
                      right: 2,
                      width: 18,
                      height: 18,
                      borderRadius: "50%",
                      bgcolor: "rgba(0,0,0,0.6)",
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                      "&:hover": { bgcolor: "rgba(0,0,0,0.8)" },
                    }}
                  >
                    <X size={10} />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.primary" fontWeight={500}>
                    Patient picture selected
                  </Typography>
                  <Typography
                    variant="caption"
                    color="secondary.main"
                    sx={{ cursor: "pointer", "&:hover": { textDecoration: "underline" } }}
                    onClick={() => setPickerOpen(true)}
                  >
                    Change image
                  </Typography>
                </Box>
              </>
            ) : (
              <Button
                variant="outlined"
                startIcon={<ImageIcon size={16} />}
                onClick={() => setPickerOpen(true)}
                sx={{
                  color: "text.secondary",
                  borderColor: "divider",
                  borderStyle: "dashed",
                  py: 1.5,
                  px: 3,
                  textTransform: "none",
                }}
              >
                Add patient picture
              </Button>
            )}
          </Box>

          {editCase && (
            <>
              <Divider />
              <Typography variant="subtitle2" fontWeight={600}>
                2D practice visemes
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                B–H, X, and blink are image-to-image from the same <strong>A.png</strong>. Either upload A.png, or
                check <strong>Generate base face from prompt</strong> and describe the character (e.g. cartoon doctor)
                so the server creates A.png with text-to-image first.{" "}
                {editCase.viseme_shapes_base_url
                  ? `Active URL prefix: ${editCase.viseme_shapes_base_url}`
                  : "No custom set yet — defaults to global /static/shapes/ until generation succeeds."}
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={generateBaseFromPrompt}
                    onChange={(e) => setGenerateBaseFromPrompt(e.target.checked)}
                    size="small"
                  />
                }
                label="Generate base face from prompt (no reference upload needed)"
              />
              <input
                ref={visemeFileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  e.target.value = "";
                  if (f) void uploadVisemeReference(f);
                }}
              />
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={visemeUploading || !!visemeJobId || generateBaseFromPrompt}
                  onClick={() => visemeFileRef.current?.click()}
                >
                  Upload viseme reference (A.png)
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  color="secondary"
                  disabled={!!visemeJobId || visemeUploading}
                  onClick={() => void startVisemeGeneration()}
                >
                  Generate B–H, X, blink
                </Button>
              </Box>
              <TextField
                label="Prompt (character / style)"
                fullWidth
                size="small"
                value={visemePrompt}
                onChange={(e) => setVisemePrompt(e.target.value)}
                placeholder="e.g. middle-aged woman, soft lighting, medical patient portrait"
              />
              <TextField
                label="Extra character hint (optional)"
                fullWidth
                size="small"
                value={visemeHint}
                onChange={(e) => setVisemeHint(e.target.value)}
              />
              {visemeStatusLine && (
                <Typography variant="caption" color="text.secondary">
                  {visemeStatusLine}
                </Typography>
              )}
            </>
          )}

          {/* Row 6: System prompt */}
          <TextField
            label="System prompt (patient persona)"
            fullWidth
            multiline
            rows={8}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            required
            placeholder="You are [patient name], a [age]-year-old..."
            sx={{
              "& .MuiInputBase-root": { fontFamily: '"Roboto Mono", monospace', fontSize: "0.85rem" },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={onClose} disabled={saving}>Cancel</Button>
          <PrimaryButton onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving..." : editCase ? "Save changes" : "Create case"}
          </PrimaryButton>
        </DialogActions>
      </Dialog>

      {/* Avatar picker modal */}
      <AvatarPickerDialog
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={handleAvatarSelect}
        currentFilename={selectedLibraryFile}
      />
    </>
  );
}
