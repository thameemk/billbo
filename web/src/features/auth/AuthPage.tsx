import PaymentsIcon from "@mui/icons-material/Payments";
import {Avatar, Box, Button, Container, TextField, Typography} from "@mui/material";
import {useState, type FormEvent} from "react";
import * as api from "../../api/auth.ts";

export function AuthPage({onLogin}: { onLogin: () => void }) {
    const [mode, setMode] = useState<"login" | "register">("login");
    const [err, setErr] = useState("");
    const [busy, setBusy] = useState(false);

    async function submit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const [name, email, pw] = ["name", "email", "password"].map((k) => String(f.get(k) ?? ""));
        setBusy(true);
        setErr("");
        try {
            if (mode === "register") await api.register(name, email, pw);
            await api.login(email, pw);
            onLogin();
        } catch (x) {
            setErr((x as Error).message);
        } finally {
            setBusy(false);
        }
    }

    return (
        <Container maxWidth="xs" sx={{minHeight: "100vh", display: "flex", alignItems: "center"}}>
            <Box component="form" onSubmit={submit} sx={{width: 1, display: "flex", flexDirection: "column", gap: 2}}>
                <Avatar sx={{bgcolor: "primary.main", width: 56, height: 56}}><PaymentsIcon/></Avatar>
                <Box>
                    <Typography variant="h4"
                                fontWeight={700}>{mode === "login" ? "Welcome back" : "Create account"}</Typography>
                    <Typography color="text.secondary">Split expenses with friends, simply.</Typography>
                </Box>
                {mode === "register" && <TextField name="name" label="Your name"/>}
                <TextField name="email" type="email" label="Email" required/>
                <TextField name="password" type="password" label="Password" required
                           slotProps={{htmlInput: {minLength: 8}}}
                           helperText={mode === "register" ? "At least 8 characters" : undefined}/>
                {err && <Typography color="error" variant="body2">{err}</Typography>}
                <Button type="submit" variant="contained" size="large" disabled={busy}>
                    {busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
                </Button>
                <Button onClick={() => {
                    setErr("");
                    setMode(mode === "login" ? "register" : "login");
                }}>
                    {mode === "login" ? "New here? Sign up" : "Have an account? Log in"}
                </Button>
            </Box>
        </Container>
    );
}
