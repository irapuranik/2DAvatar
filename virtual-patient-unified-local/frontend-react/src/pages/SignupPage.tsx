import { useState, FormEvent } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import { Stethoscope } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { PrimaryButton } from "../components/styled";
import { ElevatedCard } from "../components/styled";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const { signup, isLoading, error } = useAuthStore();

  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) return;
    try {
      const result = await signup(email, password, displayName);
      if (result === "confirmation_needed") {
        setSuccess(true);
      }
      // if "logged_in", the App router will redirect automatically
    } catch {
      // error is set in store
    }
  };

  if (success) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "background.default",
          p: 2,
        }}
      >
        <ElevatedCard sx={{ maxWidth: 420, width: "100%", p: 4, textAlign: "center" }}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              bgcolor: "success.main",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              mx: "auto",
              mb: 2,
            }}
          >
            <Stethoscope size={28} color="#FFFFFF" />
          </Box>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            Check your email
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            We sent a confirmation link to <strong>{email}</strong>. Click it to activate
            your account, then come back here to sign in.
          </Typography>
          <Link to="/login" style={{ color: "inherit", fontWeight: 600 }}>
            Back to Sign in
          </Link>
        </ElevatedCard>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        p: 2,
      }}
    >
      <ElevatedCard sx={{ maxWidth: 420, width: "100%", p: 4 }}>
        <Box sx={{ textAlign: "center", mb: 4 }}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              bgcolor: "primary.main",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              mx: "auto",
              mb: 2,
            }}
          >
            <Stethoscope size={28} color="#FFFFFF" />
          </Box>
          <Typography variant="h4" fontWeight={600} gutterBottom>
            Student Sign Up
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a student account to practice with virtual patients
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 1 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Full Name"
            fullWidth
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
            autoFocus
            sx={{ mb: 2 }}
          />
          <TextField
            label="Email"
            type="email"
            fullWidth
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            helperText="At least 6 characters"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Confirm Password"
            type="password"
            fullWidth
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            error={passwordMismatch}
            helperText={passwordMismatch ? "Passwords don't match" : ""}
            sx={{ mb: 3 }}
          />
          <PrimaryButton
            type="submit"
            fullWidth
            size="large"
            disabled={
              isLoading ||
              !email ||
              !password ||
              !displayName ||
              password !== confirmPassword ||
              password.length < 6
            }
          >
            {isLoading ? <CircularProgress size={22} color="inherit" /> : "Create Account"}
          </PrimaryButton>
        </form>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: "center" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "inherit", fontWeight: 600 }}>
            Sign in
          </Link>
        </Typography>
      </ElevatedCard>
    </Box>
  );
}
