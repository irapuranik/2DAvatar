import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Paper from "@mui/material/Paper";
import CircularProgress from "@mui/material/CircularProgress";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import { Save } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";
import { PrimaryButton, SmallText } from "./styled";

export default function GlobalPrompt() {
  const { token } = useAuthStore();
  const [prompt, setPrompt] = useState("");
  const [savedPrompt, setSavedPrompt] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!token) return;
    apiFetch<{ prompt: string }>("/settings/global-prompt", { token })
      .then((data) => {
        setPrompt(data.prompt);
        setSavedPrompt(data.prompt);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const hasChanges = prompt !== savedPrompt;

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    try {
      await apiFetch("/settings/global-prompt", {
        method: "PUT",
        body: { prompt },
        token,
      });
      setSavedPrompt(prompt);
      setSnack({ message: "Global prompt saved", severity: "success" });
    } catch {
      setSnack({ message: "Failed to save", severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" fontWeight={600}>
          Global Prompt
        </Typography>
        <SmallText>
          This prompt is automatically prepended to every case's system prompt. Use it for
          universal instructions that should apply across all patient scenarios.
        </SmallText>
      </Box>

      <Paper sx={{ p: 3, borderRadius: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <Typography variant="subtitle2" fontWeight={600}>
            Standard instructions
          </Typography>
          {hasChanges && (
            <Chip size="small" label="Unsaved changes" color="warning" sx={{ height: 22 }} />
          )}
          {!hasChanges && savedPrompt && (
            <Chip size="small" label="Saved" color="success" variant="outlined" sx={{ height: 22 }} />
          )}
        </Box>

        <TextField
          fullWidth
          multiline
          minRows={8}
          maxRows={20}
          placeholder="Enter global instructions that will be applied to all cases...&#10;&#10;Example: You are a standardized patient in a medical training simulation. Always stay in character. Keep responses realistic and concise."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          sx={{
            mb: 2,
            "& .MuiOutlinedInput-root": { borderRadius: 2 },
          }}
        />

        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <PrimaryButton
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : <Save size={16} />}
            onClick={handleSave}
            disabled={saving || !hasChanges}
          >
            {saving ? "Saving..." : "Save"}
          </PrimaryButton>
          <SmallText>
            {prompt.length > 0
              ? `${prompt.length} characters`
              : "No global prompt set — each case will only use its own prompt"}
          </SmallText>
        </Box>
      </Paper>

      <Paper sx={{ p: 2.5, borderRadius: 2, mt: 2, bgcolor: "action.hover" }}>
        <Typography variant="caption" color="text.secondary">
          <strong>How it works:</strong> When a student starts a practice session, the system prompt
          sent to the AI is constructed as: <em>Global Prompt</em> + <em>Case Prompt</em>. The global
          prompt comes first, followed by the case-specific prompt set during case creation.
          If the global prompt is empty, only the case prompt is used.
        </Typography>
      </Paper>

      <Snackbar
        open={!!snack}
        autoHideDuration={3000}
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
