import { useState, useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import { UserX, Users, ShieldCheck, GraduationCap } from "lucide-react";
import { useAuthStore, User } from "../stores/authStore";
import { apiFetch } from "../api/client";
import { PageTitle, FlexBetween } from "./styled";

export default function UserManagement() {
  const { token } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);

  const fetchUsers = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch<User[]>("/auth/users", { token });
      setUsers(data);
    } catch (err: any) {
      setSnack({ message: err.message, severity: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleToggleRole = async (user: User) => {
    if (!token) return;
    const newRole = user.role === "admin" ? "student" : "admin";
    try {
      await apiFetch(`/auth/users/${user.id}/role`, {
        method: "PATCH",
        body: { role: newRole },
        token,
      });
      setSnack({ message: `"${user.display_name}" is now ${newRole}`, severity: "success" });
      fetchUsers();
    } catch (err: any) {
      setSnack({ message: err.message, severity: "error" });
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!token) return;
    try {
      await apiFetch(`/auth/users/${user.id}`, { method: "DELETE", token });
      setSnack({ message: `"${user.display_name}" deactivated`, severity: "success" });
      fetchUsers();
    } catch (err: any) {
      setSnack({ message: err.message, severity: "error" });
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <Box>
      <FlexBetween sx={{ mb: 3 }}>
        <Box>
          <PageTitle>Users</PageTitle>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Users sign up via the signup page. Manage roles and access here.
          </Typography>
        </Box>
      </FlexBetween>

      {loading ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : users.length === 0 ? (
        <Paper sx={{ textAlign: "center", py: 8, px: 3, borderRadius: 2 }}>
          <Users size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
          <Typography variant="h6" color="text.secondary">
            No users yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Users will appear here after they sign up.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Email</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Role</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Joined</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((u) => (
                <TableRow
                  key={u.id}
                  hover
                  sx={{ "&:hover": { bgcolor: (t) => `${t.palette.secondary.main}0A` } }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>{u.display_name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">{u.email}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.role === "admin" ? "Admin" : "Student"}
                      size="small"
                      color={u.role === "admin" ? "primary" : "secondary"}
                      sx={{ fontWeight: 500 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.is_active ? "Active" : "Inactive"}
                      size="small"
                      color={u.is_active ? "success" : "default"}
                      variant={u.is_active ? "filled" : "outlined"}
                      sx={{ fontWeight: 500 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(u.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title={u.role === "admin" ? "Make student" : "Make admin"}>
                      <IconButton size="small" onClick={() => handleToggleRole(u)}>
                        {u.role === "admin" ? <GraduationCap size={16} /> : <ShieldCheck size={16} />}
                      </IconButton>
                    </Tooltip>
                    {u.is_active && (
                      <Tooltip title="Deactivate user">
                        <IconButton size="small" color="error" onClick={() => handleDeactivate(u)}>
                          <UserX size={16} />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setSnack(null)}
          severity={snack?.severity || "success"}
          variant="filled"
          sx={{ borderRadius: 1 }}
        >
          {snack?.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
