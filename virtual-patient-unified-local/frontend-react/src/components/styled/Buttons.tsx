import { styled } from "@mui/material/styles";
import Button from "@mui/material/Button";

export const PrimaryButton = styled((props: any) => <Button variant="contained" {...props} />)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: "#FFFFFF",
  "&:hover": {
    backgroundColor: theme.palette.primary.dark,
    boxShadow: theme.shadows[4],
    transform: "translateY(-1px)",
  },
  "&:active": {
    transform: "translateY(0)",
    boxShadow: theme.shadows[2],
  },
}));

export const SecondaryButton = styled((props: any) => <Button variant="contained" {...props} />)(({ theme }) => ({
  backgroundColor: theme.palette.secondary.main,
  color: "#FFFFFF",
  "&:hover": {
    backgroundColor: theme.palette.secondary.dark,
    boxShadow: theme.shadows[4],
    transform: "translateY(-1px)",
  },
  "&:active": {
    transform: "translateY(0)",
    boxShadow: theme.shadows[2],
  },
}));

export const DangerButton = styled((props: any) => <Button variant="contained" {...props} />)(({ theme }) => ({
  backgroundColor: theme.palette.error.main,
  color: "#FFFFFF",
  "&:hover": {
    backgroundColor: theme.palette.error.dark,
    boxShadow: theme.shadows[4],
    transform: "translateY(-1px)",
  },
}));

export const OutlinedButton = styled((props: any) => <Button variant="outlined" {...props} />)(({ theme }) => ({
  borderColor: theme.palette.primary.main,
  color: theme.palette.primary.main,
  "&:hover": {
    backgroundColor: theme.palette.primary.main,
    color: "#FFFFFF",
    transform: "translateY(-1px)",
  },
}));
