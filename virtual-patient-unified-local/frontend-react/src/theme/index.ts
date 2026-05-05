import { createTheme } from "@mui/material/styles";
import { lightPalette, darkPalette } from "./palettes";
import { typography } from "./typography";
import { getComponentOverrides } from "./components";

function buildTheme(mode: "light" | "dark") {
  const palette = mode === "light" ? lightPalette : darkPalette;

  const base = createTheme({
    palette,
    typography,
    spacing: 8,
    shape: { borderRadius: 4 },
    breakpoints: {
      values: { xs: 0, sm: 600, md: 960, lg: 1280, xl: 1920 },
    },
  });

  return createTheme(base, {
    components: getComponentOverrides(base),
  });
}

export const lightTheme = buildTheme("light");
export const darkTheme = buildTheme("dark");
