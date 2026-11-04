import LogoutIcon from "@mui/icons-material/Logout";
import {Avatar, Box, Button, Card, CardContent, Divider, Stack, Typography} from "@mui/material";
import {useEffect, useState} from "react";
import * as auth from "../../api/auth.ts";
import {fmt, type Group} from "../../lib/money.ts";

export function ProfilePage({groups, onLogout}: {
    groups: Group[]; onLogout: () => void;
}) {
    const [user, setUser] = useState<auth.User | null>(null);
    const [err, setErr] = useState("");
    useEffect(() => {
        auth.me().then(setUser).catch((e: Error) => setErr(e.message));
    }, []);

    const name = user?.display_name || user?.email.split("@")[0] || "";
    // one figure per currency: amounts in different currencies can't be added together
    const totals = new Map<string, number>();
    for (const g of groups) totals.set(g.currency, (totals.get(g.currency) ?? 0) + g.cents);
    const stats: [string, string][] = [
        ["Groups", String(groups.length)],
        ["Expenses", String(groups.reduce((n, g) => n + g.count, 0))],
        ["Total spent", [...totals].map(([currency, cents]) => fmt(cents, currency)).join(" · ") || fmt(0)],
    ];
    return (
        <Stack spacing={3} alignItems="center">
            <Stack alignItems="center" spacing={1} sx={{pt: 2}}>
                <Avatar sx={{
                    width: 88,
                    height: 88,
                    fontSize: 36,
                    bgcolor: "primary.main"
                }}>{name[0]?.toUpperCase()}</Avatar>
                <Typography variant="h5" fontWeight={700}>{name || "…"}</Typography>
                <Typography color="text.secondary">{user?.email}</Typography>
                {err && <Typography color="error" variant="body2">{err}</Typography>}
            </Stack>
            <Card sx={{width: 1}}>
                <CardContent sx={{display: "flex"}}>
                    {stats.map(([label, value], i) => (
                        <Box key={label} sx={{display: "flex", flex: 1}}>
                            {i > 0 && <Divider orientation="vertical" flexItem/>}
                            <Box sx={{flex: 1, textAlign: "center"}}>
                                <Typography fontWeight={700}>{value}</Typography>
                                <Typography variant="body2" color="text.secondary">{label}</Typography>
                            </Box>
                        </Box>
                    ))}
                </CardContent>
            </Card>
            <Button variant="outlined" color="error" startIcon={<LogoutIcon/>} onClick={onLogout}>Log out</Button>
        </Stack>
    );
}
