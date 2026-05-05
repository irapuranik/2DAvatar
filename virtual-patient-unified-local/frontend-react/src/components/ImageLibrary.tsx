import { useEffect, useState, useRef, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import IconButton from "@mui/material/IconButton";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import { Plus, Trash2, Upload } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch, BACKEND_URL } from "../api/client";

interface LibraryImage {
  filename: string;
  url: string;
}
import { PageTitle, PrimaryButton, DangerButton, FlexBetween } from "./styled";

export default function ImageLibrary() {
  const { token } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [images, setImages] = useState<LibraryImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<LibraryImage | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);

  const fetchImages = useCallback(async () => {
    if (!token) return;
    try {
      const res = await apiFetch<{ images: LibraryImage[] }>("/cases/avatars/library", { token });
      setImages(res.images);
    } catch (err: any) {
      setSnack({ message: err.message || "Failed to load images", severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchImages();
  }, [fetchImages]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !token) return;

    setUploading(true);
    let successCount = 0;
    let lastError = "";

    for (const file of Array.from(files)) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        await fetch(`${BACKEND_URL}/api/cases/avatars/library`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }).then(async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Upload failed" }));
            throw new Error(err.detail);
          }
          successCount++;
        });
      } catch (err: any) {
        lastError = err.message;
      }
    }

    setUploading(false);
    // Reset the file input
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (successCount > 0) {
      setSnack({
        message: `${successCount} image${successCount > 1 ? "s" : ""} uploaded`,
        severity: "success",
      });
      fetchImages();
    }
    if (lastError) {
      setSnack({ message: lastError, severity: "error" });
    }
  };

  const handleDelete = async () => {
    if (!token || !deleteTarget) return;
    setDeleting(true);
    try {
      await apiFetch(`/cases/avatars/library/${encodeURIComponent(deleteTarget.filename)}`, {
        method: "DELETE",
        token,
      });
      setSnack({ message: `"${deleteTarget.filename}" deleted`, severity: "success" });
      setDeleteTarget(null);
      fetchImages();
    } catch (err: any) {
      setSnack({ message: err.message || "Delete failed", severity: "error" });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box>
      <FlexBetween sx={{ mb: 3 }}>
        <Box>
          <PageTitle>Image Library</PageTitle>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Manage patient avatar images available when creating cases
          </Typography>
        </Box>
        <PrimaryButton
          startIcon={uploading ? <CircularProgress size={14} color="inherit" /> : <Plus size={16} />}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Upload images"}
        </PrimaryButton>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          hidden
          onChange={handleUpload}
        />
      </FlexBetween>

      {loading ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : images.length === 0 ? (
        <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
          <Upload size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No images yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload patient avatar images so they can be used when creating cases.
          </Typography>
          <PrimaryButton
            startIcon={<Plus size={16} />}
            onClick={() => fileInputRef.current?.click()}
          >
            Upload first image
          </PrimaryButton>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {images.map((img) => (
              <Grid size={{ xs: 6, sm: 4, md: 3, lg: 2 }} key={img.filename}>
                <Paper
                  sx={{
                    borderRadius: 2,
                    overflow: "hidden",
                    position: "relative",
                    "&:hover .delete-btn": { opacity: 1 },
                    transition: "box-shadow 0.2s",
                    "&:hover": { boxShadow: 3 },
                  }}
                >
                  <Box
                    component="img"
                    src={img.url}
                    alt={img.filename}
                    sx={{
                      width: "100%",
                      height: 180,
                      objectFit: "cover",
                      objectPosition: "center 20%",
                      display: "block",
                    }}
                  />
                  {/* Delete button overlay */}
                  <Tooltip title="Delete image">
                    <IconButton
                      className="delete-btn"
                      size="small"
                      onClick={() => setDeleteTarget(img)}
                      sx={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        bgcolor: "rgba(0,0,0,0.6)",
                        color: "#fff",
                        opacity: 0,
                        transition: "opacity 0.2s",
                        "&:hover": { bgcolor: "error.main" },
                      }}
                    >
                      <Trash2 size={14} />
                    </IconButton>
                  </Tooltip>
                  {/* Filename */}
                  <Box sx={{ px: 1.5, py: 1 }}>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      noWrap
                      sx={{ display: "block" }}
                    >
                      {img.filename}
                    </Typography>
                  </Box>
                </Paper>
              </Grid>
          ))}
        </Grid>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete image</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{deleteTarget?.filename}"? Cases currently using this image will keep their reference but the image will no longer load.
          </Typography>
          {deleteTarget && (
            <Box sx={{ mt: 2, textAlign: "center" }}>
              <Box
                component="img"
                src={deleteTarget.url}
                sx={{
                  maxWidth: 200,
                  maxHeight: 200,
                  borderRadius: 1,
                  objectFit: "cover",
                  objectPosition: "center 20%",
                }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
          <DangerButton onClick={handleDelete} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete"}
          </DangerButton>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
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
