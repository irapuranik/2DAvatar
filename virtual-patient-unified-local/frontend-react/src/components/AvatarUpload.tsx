import { useState, useRef, useCallback, useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import { Upload, X, Image as ImageIcon, Check } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { apiFetch } from "../api/client";

interface LibraryImage {
  filename: string;
  url: string;
}

interface AvatarUploadProps {
  /** URL of the currently selected avatar (when editing an existing case) */
  currentUrl?: string | null;
  /** Filename selected from the library (not a file upload) */
  selectedLibraryFile?: string | null;
  /** Called when a local file is chosen via drag-drop or file picker */
  onFileSelected: (file: File) => void;
  /** Called when a library avatar is picked by filename */
  onLibrarySelected?: (filename: string) => void;
  /** Called when the avatar is removed */
  onRemove?: () => void;
  disabled?: boolean;
}

export default function AvatarUpload({
  currentUrl,
  selectedLibraryFile,
  onFileSelected,
  onLibrarySelected,
  onRemove,
  disabled,
}: AvatarUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [libraryImages, setLibraryImages] = useState<LibraryImage[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { token } = useAuthStore();

  // Fetch avatar library on mount
  useEffect(() => {
    if (!token) return;
    setLibraryLoading(true);
    apiFetch<{ images: LibraryImage[] }>("/cases/avatars/library", { token })
      .then((res) => setLibraryImages(res.images))
      .catch(() => setLibraryImages([]))
      .finally(() => setLibraryLoading(false));
  }, [token]);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(file);
      onFileSelected(file);
    },
    [onFileSelected],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleRemove = () => {
    setPreview(null);
    if (inputRef.current) inputRef.current.value = "";
    onRemove?.();
  };

  const handleLibraryPick = (filename: string) => {
    setPreview(null); // Clear any custom upload preview
    onLibrarySelected?.(filename);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      {/* Library gallery */}
      {libraryLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={20} />
        </Box>
      ) : libraryImages.length > 0 ? (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
            Patient picture
          </Typography>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(64px, 1fr))",
              gap: 0.75,
              maxHeight: 200,
              overflowY: "auto",
            }}
          >
            {libraryImages.map((img) => {
              const isSelected = selectedLibraryFile === img.filename
                || (!selectedLibraryFile && !preview && currentUrl === img.url);
              return (
                <Box
                  key={img.filename}
                  onClick={() => !disabled && handleLibraryPick(img.filename)}
                  sx={{
                    position: "relative",
                    width: "100%",
                    aspectRatio: "1",
                    borderRadius: 1,
                    overflow: "hidden",
                    cursor: disabled ? "default" : "pointer",
                    border: 2,
                    borderColor: isSelected ? "secondary.main" : "transparent",
                    opacity: disabled ? 0.5 : 1,
                    transition: "all 0.15s",
                    "&:hover": disabled ? {} : { borderColor: "secondary.light", transform: "scale(1.04)" },
                  }}
                >
                  <Box
                    component="img"
                    src={img.url}
                    alt={img.filename}
                    loading="lazy"
                    sx={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                  {isSelected && (
                    <Box
                      sx={{
                        position: "absolute",
                        inset: 0,
                        bgcolor: "rgba(0,0,0,0.35)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Check size={20} color="#fff" />
                    </Box>
                  )}
                </Box>
              );
            })}
          </Box>
        </Box>
      ) : null}

      {/* Divider between library and upload */}
      {libraryImages.length > 0 && (
        <Divider sx={{ fontSize: "0.7rem", color: "text.disabled" }}>or upload your own</Divider>
      )}

      {/* Upload drop zone */}
      <Box
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        sx={{
          position: "relative",
          width: "100%",
          minHeight: preview ? 160 : 72,
          border: 2,
          borderStyle: "dashed",
          borderColor: dragOver ? "secondary.main" : "divider",
          borderRadius: 2,
          bgcolor: dragOver ? "action.hover" : "background.default",
          cursor: disabled ? "default" : "pointer",
          overflow: "hidden",
          transition: "all 0.2s ease-in-out",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          "&:hover": disabled ? {} : { borderColor: "secondary.main", bgcolor: "action.hover" },
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleChange}
          hidden
          disabled={disabled}
        />

        {preview ? (
          <>
            <Box
              component="img"
              src={preview}
              alt="Custom upload preview"
              sx={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
            {!disabled && (
              <IconButton
                size="small"
                onClick={(e) => { e.stopPropagation(); handleRemove(); }}
                sx={{
                  position: "absolute",
                  top: 6,
                  right: 6,
                  bgcolor: "rgba(0,0,0,0.6)",
                  color: "#fff",
                  "&:hover": { bgcolor: "rgba(0,0,0,0.8)" },
                  width: 28,
                  height: 28,
                }}
              >
                <X size={14} />
              </IconButton>
            )}
          </>
        ) : (
          <Box sx={{ textAlign: "center", px: 2, py: 1 }}>
            {dragOver ? (
              <Upload size={24} style={{ opacity: 0.5, marginBottom: 4 }} />
            ) : (
              <ImageIcon size={24} style={{ opacity: 0.3, marginBottom: 4 }} />
            )}
            <Typography variant="caption" color="text.secondary" display="block">
              {dragOver ? "Drop image here" : "Upload image"}
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}
