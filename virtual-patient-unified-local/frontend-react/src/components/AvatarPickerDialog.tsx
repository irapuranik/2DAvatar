import { useState, useEffect, useRef, useCallback } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import CircularProgress from "@mui/material/CircularProgress";
import { Upload, X, Check, Image as ImageIcon } from "lucide-react";
import { PrimaryButton } from "./styled";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";

interface LibraryImage {
  filename: string;
  url: string;
}

export interface AvatarSelection {
  type: "library" | "upload";
  filename?: string;    // for library picks
  file?: File;          // for custom uploads
  previewUrl: string;   // for display
}

interface AvatarPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (selection: AvatarSelection) => void;
  currentFilename?: string | null;
}

export default function AvatarPickerDialog({
  open,
  onClose,
  onSelect,
  currentFilename,
}: AvatarPickerDialogProps) {
  const { token } = useAuthStore();
  const [libraryImages, setLibraryImages] = useState<LibraryImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch library on open
  useEffect(() => {
    if (open && token) {
      setLoading(true);
      apiFetch<{ images: LibraryImage[] }>("/cases/avatars/library", { token })
        .then((d) => setLibraryImages(d.images))
        .catch((err) => console.error("Avatar library error:", err.message))
        .finally(() => setLoading(false));
    }
  }, [open, token]);

  // Reset state when opening
  useEffect(() => {
    if (open) {
      setSelected(currentFilename || null);
      setUploadFile(null);
      setUploadPreview(null);
    }
  }, [open, currentFilename]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (ev) => setUploadPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
    setUploadFile(file);
    setSelected(null); // clear library selection
  }, []);

  const handleLibraryPick = (filename: string) => {
    setSelected(filename);
    setUploadFile(null);
    setUploadPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleConfirm = () => {
    if (uploadFile && uploadPreview) {
      onSelect({ type: "upload", file: uploadFile, previewUrl: uploadPreview });
    } else if (selected) {
      const img = libraryImages.find((i) => i.filename === selected);
      onSelect({
        type: "library",
        filename: selected,
        previewUrl: img?.url || "",
      });
    }
    onClose();
  };

  const handleRemoveUpload = () => {
    setUploadFile(null);
    setUploadPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const hasSelection = !!(selected || uploadFile);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontWeight: 600 }}>
        Choose patient picture
      </DialogTitle>

      <DialogContent sx={{ pb: 1 }}>
        {/* Library grid */}
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        ) : libraryImages.length > 0 ? (
          <>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
              Select from library
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 1,
                mb: 2,
              }}
            >
              {libraryImages.map((img) => {
                const isSelected = selected === img.filename && !uploadFile;
                return (
                  <Box
                    key={img.filename}
                    onClick={() => handleLibraryPick(img.filename)}
                    sx={{
                      position: "relative",
                      cursor: "pointer",
                      borderRadius: 1.5,
                      overflow: "hidden",
                      border: "3px solid",
                      borderColor: isSelected ? "secondary.main" : "transparent",
                      transition: "all 0.15s",
                      "&:hover": {
                        borderColor: isSelected ? "secondary.main" : "action.selected",
                        transform: "scale(1.03)",
                      },
                    }}
                  >
                    <Box
                      component="img"
                      src={img.url}
                      alt={img.filename}
                      loading="lazy"
                      sx={{
                        width: "100%",
                        aspectRatio: "1",
                        objectFit: "cover",
                        objectPosition: "top",
                        display: "block",
                      }}
                    />
                    {isSelected && (
                      <Box
                        sx={{
                          position: "absolute",
                          inset: 0,
                          bgcolor: "rgba(0,0,0,0.3)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Box
                          sx={{
                            width: 28,
                            height: 28,
                            borderRadius: "50%",
                            bgcolor: "secondary.main",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <Check size={16} color="#fff" />
                        </Box>
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Box>
          </>
        ) : (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <ImageIcon size={32} style={{ opacity: 0.2, marginBottom: 8 }} />
            <Typography variant="body2" color="text.disabled">
              No images in library yet
            </Typography>
          </Box>
        )}

        {/* Divider + upload */}
        <Divider sx={{ my: 2 }}>
          <Typography variant="caption" color="text.disabled">or upload your own</Typography>
        </Divider>

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={handleFileChange}
        />

        {uploadPreview ? (
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
            <Box
              sx={{
                position: "relative",
                width: 90,
                flexShrink: 0,
                borderRadius: 1.5,
                overflow: "hidden",
                border: "3px solid",
                borderColor: "secondary.main",
              }}
            >
              <Box
                component="img"
                src={uploadPreview}
                sx={{
                  width: "100%",
                  aspectRatio: "3/4",
                  objectFit: "cover",
                  objectPosition: "top",
                  display: "block",
                }}
              />
              <Box
                onClick={handleRemoveUpload}
                sx={{
                  position: "absolute",
                  top: 4,
                  right: 4,
                  width: 22,
                  height: 22,
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
                <X size={12} />
              </Box>
            </Box>
            <Box sx={{ pt: 1 }}>
              <Typography variant="body2" fontWeight={500}>
                Custom image selected
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {uploadFile?.name}
              </Typography>
            </Box>
          </Box>
        ) : (
          <Button
            variant="outlined"
            size="small"
            startIcon={<Upload size={14} />}
            onClick={() => inputRef.current?.click()}
            fullWidth
            sx={{ color: "text.secondary", borderColor: "divider", py: 1 }}
          >
            Upload image
          </Button>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <PrimaryButton onClick={handleConfirm} disabled={!hasSelection}>
          Select
        </PrimaryButton>
      </DialogActions>
    </Dialog>
  );
}
