// AIMMS Design System — University of Arizona brand palettes

export const lightPalette = {
  mode: "light" as const,
  primary: {
    main: "#AB0520",    // Arizona Red
    dark: "#8B0015",    // Chili
    light: "#0C234B",   // Arizona Blue
    contrastText: "#FFFFFF",
  },
  secondary: {
    main: "#1E5288",    // Azurite
    dark: "#001C48",    // Midnight
    light: "#378DBD",   // Oasis
    contrastText: "#FFFFFF",
  },
  error: {
    main: "#AB0520",
    dark: "#8B0015",
    light: "#D32F2F",
  },
  warning: {
    main: "#F57C00",
    dark: "#E65100",
    light: "#FF9800",
  },
  success: {
    main: "#1B5E20",
    dark: "#0D4715",
    light: "#2E7D32",
  },
  info: {
    main: "#1E5288",
    dark: "#0C234B",
    light: "#378DBD",
  },
  background: {
    default: "#F8FAFC",
    paper: "#FFFFFF",
  },
  text: {
    primary: "#001C48",
    secondary: "#475569",
    disabled: "#94A3B8",
  },
  divider: "#E2E8F0",
};

export const darkPalette = {
  mode: "dark" as const,
  primary: {
    main: "#2DD4BF",
    dark: "#14B8A6",
    light: "#5EEAD4",
    contrastText: "#0a0e1a",
  },
  secondary: {
    main: "#6EC5FF",
    dark: "#4DA3D4",
    light: "#A8DDFF",
    contrastText: "#0a0e1a",
  },
  error: { main: "#F87171" },
  warning: { main: "#FBBF24" },
  success: { main: "#A78BFA" },
  info: { main: "#60A5FA" },
  background: {
    default: "#0a0e1a",
    paper: "#1e2536",
  },
  text: {
    primary: "#F9FAFB",
    secondary: "#E5E7EB",
    disabled: "#9CA3AF",
  },
  divider: "rgba(255, 255, 255, 0.25)",
};
