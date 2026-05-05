import Chip, { ChipProps } from "@mui/material/Chip";

interface StatusChipProps extends Omit<ChipProps, "color"> {
  status: "draft" | "published";
}

export function StatusChip({ status, ...rest }: StatusChipProps) {
  const config = status === "published"
    ? { label: "Published", color: "success" as const }
    : { label: "Draft", color: "default" as const };

  return (
    <Chip
      size="small"
      label={config.label}
      color={config.color}
      sx={{ fontWeight: 500, borderRadius: 1 }}
      {...rest}
    />
  );
}
