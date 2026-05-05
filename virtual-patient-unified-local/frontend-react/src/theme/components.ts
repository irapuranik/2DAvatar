import { Components, Theme } from "@mui/material/styles";

export const getComponentOverrides = (theme: Theme): Components<Theme> => ({
  MuiCssBaseline: {
    styleOverrides: {
      "*": {
        scrollbarWidth: "thin",
        scrollbarColor: "rgba(0, 0, 0, 0.2) transparent",
      },
      "*::-webkit-scrollbar": { width: "3px", height: "3px" },
      "*::-webkit-scrollbar-track": { background: "transparent" },
      "*::-webkit-scrollbar-thumb": {
        background: "rgba(0, 0, 0, 0.2)",
        borderRadius: "1.5px",
      },
      "*::-webkit-scrollbar-thumb:hover": {
        background: "rgba(0, 0, 0, 0.35)",
      },
    },
  },
  MuiButton: {
    defaultProps: { disableElevation: true },
    styleOverrides: {
      root: {
        textTransform: "none",
        borderRadius: 4,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-1px)",
        },
        "&:active": {
          transform: "translateY(0)",
        },
      },
      sizeSmall: { padding: "4px 12px", fontSize: "0.8125rem" },
      sizeMedium: { padding: "8px 16px", fontSize: "0.875rem" },
      sizeLarge: { padding: "12px 24px", fontSize: "1rem" },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
        borderRadius: 8,
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        transition: "all 0.2s ease-in-out",
      },
    },
  },
  MuiTextField: {
    defaultProps: { variant: "outlined", size: "small" },
    styleOverrides: {
      root: {
        "& .MuiOutlinedInput-root": {
          transition: "all 0.25s ease-in-out",
          "& fieldset": {
            borderWidth: 1.5,
            borderColor: `${theme.palette.secondary.main}40`,
          },
          "&:hover fieldset": {
            borderColor: `${theme.palette.secondary.main}99`,
          },
          "&.Mui-focused fieldset": {
            borderColor: theme.palette.secondary.main,
            borderWidth: 2,
          },
          "&.Mui-focused": {
            transform: "translateY(-1px)",
          },
        },
        "& .MuiInputLabel-root": {
          fontWeight: 500,
          fontSize: "0.875rem",
          "&.Mui-focused": {
            color: theme.palette.secondary.main,
            fontWeight: 600,
          },
        },
      },
    },
  },
  MuiCheckbox: {
    defaultProps: { color: "secondary" },
  },
  MuiRadio: {
    defaultProps: { color: "secondary" },
  },
  MuiTab: {
    styleOverrides: {
      root: {
        textTransform: "none",
        fontWeight: 500,
        borderRadius: 0,
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: { borderRadius: 8, fontWeight: 500 },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        fontSize: "0.75rem",
        borderRadius: 8,
      },
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 12,
        backgroundImage: "none",
      },
    },
  },
});
