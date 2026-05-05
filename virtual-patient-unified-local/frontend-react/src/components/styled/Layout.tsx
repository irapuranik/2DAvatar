import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";

export const Flex = styled(Box)({
  display: "flex",
  alignItems: "center",
  gap: 8,
});

export const FlexBetween = styled(Box)({
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 8,
});

export const FlexColumn = styled(Box)({
  display: "flex",
  flexDirection: "column",
  gap: 8,
});

export const FlexCenter = styled(Box)({
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
});
