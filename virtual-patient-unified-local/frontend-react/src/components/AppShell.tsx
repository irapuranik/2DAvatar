import { ReactNode } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import { Stethoscope, Sun, Moon, LogOut } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useThemeStore } from "../stores/themeStore";
import { Flex } from "./styled";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuthStore();
  const { mode, toggle } = useThemeStore();

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <AppBar
        position="static"
        elevation={0}
        sx={{
          bgcolor: "background.paper",
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ gap: 2 }}>
          <Flex sx={{ gap: 1.5 }}>
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                bgcolor: "primary.main",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Stethoscope size={18} color="#FFFFFF" />
            </Box>
            <Typography variant="h6" color="text.primary" fontWeight={600}>
              AIMII
            </Typography>
          </Flex>

          <Box sx={{ flex: 1 }} />

          {user && (
            <Flex sx={{ gap: 2 }}>
              <Chip
                label={user.role === "admin" ? "Admin" : "Student"}
                size="small"
                color={user.role === "admin" ? "primary" : "secondary"}
                sx={{ fontWeight: 500 }}
              />
              {/* Only show display name if it differs from the role */}
              {user.display_name.toLowerCase() !== user.role.toLowerCase() && (
                <Typography variant="body2" color="text.secondary">
                  {user.display_name}
                </Typography>
              )}
              <Tooltip title={mode === "light" ? "Dark mode" : "Light mode"}>
                <IconButton onClick={toggle} size="small">
                  {mode === "light" ? <Moon size={18} /> : <Sun size={18} />}
                </IconButton>
              </Tooltip>
              <Tooltip title="Sign out">
                <IconButton onClick={logout} size="small">
                  <LogOut size={18} />
                </IconButton>
              </Tooltip>
            </Flex>
          )}
        </Toolbar>
      </AppBar>

      <Box
        component="main"
        sx={{
          flex: 1,
          bgcolor: "background.default",
          p: 3,
        }}
      >
        <Box sx={{ maxWidth: "lg", mx: "auto" }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
