import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import { lightTheme, darkTheme } from "./theme";
import { useThemeStore } from "./stores/themeStore";
import { useAuthStore } from "./stores/authStore";
import AppShell from "./components/AppShell";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import AdminDashboard from "./pages/AdminDashboard";
import StudentDashboard from "./pages/StudentDashboard";
import PracticeSession from "./pages/PracticeSession";

function AuthGuard({ children, role }: { children: React.ReactNode; role?: "admin" | "student" }) {
  const { token, user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!token || !user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/student"} replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  const { token, user, isLoading, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, []);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={
        token && user ? (
          <Navigate to={user.role === "admin" ? "/admin" : "/student"} replace />
        ) : (
          <LoginPage />
        )
      } />

      <Route path="/signup" element={
        token && user ? (
          <Navigate to={user.role === "admin" ? "/admin" : "/student"} replace />
        ) : (
          <SignupPage />
        )
      } />

      <Route path="/admin" element={
        <AuthGuard role="admin">
          <AppShell><AdminDashboard /></AppShell>
        </AuthGuard>
      } />

      <Route path="/student" element={
        <AuthGuard role="student">
          <AppShell><StudentDashboard /></AppShell>
        </AuthGuard>
      } />

      <Route path="/student/practice/:caseId" element={
        <AuthGuard role="student">
          <AppShell><PracticeSession /></AppShell>
        </AuthGuard>
      } />

      <Route path="/admin/practice/:caseId" element={
        <AuthGuard role="admin">
          <AppShell><PracticeSession /></AppShell>
        </AuthGuard>
      } />

      {/* Default redirect */}
      <Route path="*" element={
        token && user ? (
          <Navigate to={user.role === "admin" ? "/admin" : "/student"} replace />
        ) : (
          <Navigate to="/login" replace />
        )
      } />
    </Routes>
  );
}

export default function App() {
  const { mode } = useThemeStore();
  const theme = mode === "dark" ? darkTheme : lightTheme;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}
