import { styled } from "@mui/material/styles";
import Card from "@mui/material/Card";

export const StyledCard = styled(Card)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: 8,
  boxShadow: theme.shadows[2],
  transition: "all 0.2s ease-in-out",
  "&:hover": {
    boxShadow: theme.shadows[4],
  },
}));

export const ElevatedCard = styled(Card)(({ theme }) => ({
  padding: theme.spacing(4),
  borderRadius: 8,
  boxShadow: theme.shadows[4],
  transition: "all 0.2s ease-in-out",
  "&:hover": {
    boxShadow: theme.shadows[8],
    transform: "translateY(-2px)",
  },
}));

export const ClickableCard = styled(Card)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: 8,
  boxShadow: theme.shadows[2],
  cursor: "pointer",
  transition: "all 0.2s ease-in-out",
  "&:hover": {
    boxShadow: theme.shadows[6],
    transform: "translateY(-4px)",
  },
}));
