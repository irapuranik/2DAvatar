import { styled } from "@mui/material/styles";
import Typography from "@mui/material/Typography";

export const PageTitle = styled((props: any) => <Typography variant="h1" {...props} />)(({ theme }) => ({
  fontSize: "2.5rem",
  fontWeight: 600,
  lineHeight: 1.2,
  color: theme.palette.text.primary,
}));

export const SectionTitle = styled((props: any) => <Typography variant="h3" {...props} />)(({ theme }) => ({
  fontSize: "1.5rem",
  fontWeight: 500,
  lineHeight: 1.4,
  color: theme.palette.text.primary,
}));

export const CardTitle = styled((props: any) => <Typography variant="h4" {...props} />)(({ theme }) => ({
  fontSize: "1.25rem",
  fontWeight: 500,
  lineHeight: 1.4,
  color: theme.palette.text.primary,
}));

export const BodyText = styled((props: any) => <Typography variant="body1" {...props} />)(({ theme }) => ({
  fontSize: "1rem",
  lineHeight: 1.6,
  color: theme.palette.text.primary,
}));

export const SmallText = styled((props: any) => <Typography variant="body2" {...props} />)(({ theme }) => ({
  fontSize: "0.875rem",
  lineHeight: 1.6,
  color: theme.palette.text.secondary,
}));
