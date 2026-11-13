import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import SavingsOutlinedIcon from "@mui/icons-material/SavingsOutlined";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {Box, Button, Card, IconButton, LinearProgress, Typography} from "@mui/material";
import {useState, type ReactNode} from "react";
import type {Breakdown} from "../../api/expenses.ts";
import {fmt} from "../../lib/money.ts";
import {colorOf} from "../../lib/util.ts";

const TOP = 3;
const sum = (xs: Breakdown[], k: "spent" | "received", c: string) => xs.filter((x) => x.currency === c).reduce((s, x) => s + x[k], 0);
const bySpent = (xs: Breakdown[]) => [...xs].sort((a, b) => b.spent - a.spent);

function Metric({label, icon, value, color, note, wide}: { label: string; icon: ReactNode; value: string; color?: string; note: string; wide?: boolean }) {
    return (
        <Card sx={{p: {xs: 1.5, sm: 2}, gridColumn: wide ? {xs: "1 / -1", md: "auto"} : undefined}}>
            <Box sx={{display: "flex", justifyContent: "space-between", color: "text.secondary"}}>
                <Typography variant="body2">{label}</Typography>{icon}
            </Box>
            <Typography variant="h5" fontWeight={700} color={color} sx={{fontSize: {xs: "1.25rem", sm: "1.5rem"}}}>{value}</Typography>
            <Typography variant="caption" color="text.secondary">{note}</Typography>
        </Card>
    );
}

// one ranked list for groups and for tags: bars are relative to the biggest row, the % is the share of the month's spend
function Ranked({title, rows, totals, onOpen, empty}: { title: string; rows: Breakdown[]; totals: Breakdown[]; onOpen: (id: string) => void; empty: string }) {
    const [all, setAll] = useState(false);
    const shown = all ? rows : rows.slice(0, TOP);
    return (
        <Card sx={{p: {xs: 1.5, sm: 2}}}>
            <Box sx={{display: "flex", alignItems: "baseline", justifyContent: "space-between", px: 0.75, mb: 0.5}}>
                <Typography fontWeight={600}>{title}</Typography>
                {rows.length > TOP && <Button size="small" onClick={() => setAll((a) => !a)} sx={{minWidth: 0, py: 0}}>{all ? "Show less" : `View all ${rows.length}`}</Button>}
            </Box>
            {rows.length === 0 && <Typography variant="body2" color="text.secondary" sx={{px: 0.75, py: 1}}>{empty}</Typography>}
            {shown.map((r) => {
                const top = Math.max(...rows.filter((x) => x.currency === r.currency).map((x) => x.spent));
                const share = Math.round((r.spent / sum(totals, "spent", r.currency)) * 1000) / 10;
                return (
                    <Box key={`${r.id}|${r.currency}`} component="button" onClick={() => onOpen(r.id)} aria-label={`Open ${r.name}`}
                         sx={{display: "block", width: "100%", p: 0.75, border: 0, bgcolor: "transparent", font: "inherit", color: "inherit", textAlign: "left", cursor: "pointer", borderRadius: 1.5, "&:hover, &:focus-visible": {bgcolor: "action.hover"}}}>
                        <Box sx={{display: "flex", alignItems: "baseline", gap: 1}}>
                            <Typography variant="body2" noWrap sx={{flex: 1}}>{r.name}</Typography>
                            <Typography variant="body2" fontWeight={600} sx={{fontVariantNumeric: "tabular-nums"}}>{fmt(r.spent, r.currency)}</Typography>
                            <Typography variant="caption" color="text.secondary" sx={{width: 44, textAlign: "right"}}>{share}%</Typography>
                        </Box>
                        <LinearProgress variant="determinate" value={(r.spent / top) * 100} aria-label={`${r.name} share of spend`}
                                        sx={{mt: 0.75, height: 8, borderRadius: 4, bgcolor: `${colorOf(r.id)}1f`, "& .MuiLinearProgress-bar": {bgcolor: colorOf(r.id), borderRadius: 4}}}/>
                    </Box>
                );
            })}
        </Card>
    );
}

// one month at a glance: totals against last month, then where it went; tap a group or tag to open it
export function Overview({month, onMonth, canNext, groups, tags, prev, onGroup, onTag}: {
    month: string; onMonth: (delta: number) => void; canNext: boolean;
    groups: Breakdown[]; tags: Breakdown[]; prev: Breakdown[]; onGroup: (id: string) => void; onTag: (id: string) => void;
}) {
    const label = new Date(month + "-01T00:00").toLocaleDateString(undefined, {month: "long", year: "numeric"});
    const [cur] = [...new Set(groups.map((g) => g.currency))];
    // totals only make sense in one currency
    const single = new Set(groups.map((g) => g.currency)).size === 1;
    const spent = single ? sum(groups, "spent", cur) : 0;
    const received = single ? sum(groups, "received", cur) : 0;
    const net = received - spent;
    const last = (k: "spent" | "received") => (single && prev.some((p) => p.currency === cur) ? `Last month: ${fmt(sum(prev, k, cur), cur)}` : "No data last month");
    const gs = bySpent(groups).filter((g) => g.spent > 0);
    const ts = bySpent(tags).filter((t) => t.spent > 0);
    return (
        <Box sx={{mb: 2}}>
            <Card sx={{display: "inline-flex", alignItems: "center", mb: 1.5}}>
                <IconButton aria-label="Previous month" onClick={() => onMonth(-1)}><ChevronLeftIcon/></IconButton>
                <Typography fontWeight={500} sx={{minWidth: {xs: 120, sm: 140}, textAlign: "center"}}>{label}</Typography>
                <IconButton aria-label="Next month" disabled={!canNext} onClick={() => onMonth(1)}><ChevronRightIcon/></IconButton>
            </Card>
            {groups.length === 0 ? <Typography color="text.secondary" sx={{mb: 1}}>No expenses this month.</Typography> : <>
                {single && <Box sx={{display: "grid", gap: 1.5, gridTemplateColumns: {xs: "1fr 1fr", md: "repeat(3, 1fr)"}, mb: 1.5}}>
                    <Metric label="Total spent" icon={<TrendingDownIcon fontSize="small"/>} value={fmt(spent, cur)} note={last("spent")}/>
                    <Metric label="Total received" icon={<TrendingUpIcon fontSize="small" color="success"/>} value={fmt(received, cur)} color="success.main" note={last("received")}/>
                    <Metric label="Net balance" icon={<SavingsOutlinedIcon fontSize="small"/>} value={`${net < 0 ? "-" : ""}${fmt(Math.abs(net), cur)}`} color={net < 0 ? "error.main" : "success.main"} note={net < 0 ? "Deficit this month" : "Surplus this month"} wide/>
                </Box>}
                <Box sx={{display: "grid", gap: 1.5, gridTemplateColumns: {xs: "1fr", md: "1fr 1fr"}, alignItems: "start"}}>
                    <Ranked title="Groups" rows={gs} totals={groups} onOpen={onGroup} empty="No spending in any group."/>
                    <Ranked title="Tags" rows={ts} totals={groups} onOpen={onTag} empty="Tag your expenses to see where the money goes."/>
                </Box>
            </>}
        </Box>
    );
}
