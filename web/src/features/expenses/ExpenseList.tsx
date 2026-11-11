import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import {
    Box,
    Button,
    Chip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Divider,
    IconButton,
    List,
    ListItem,
    ListItemButton,
    ListItemText,
    Typography
} from "@mui/material";
import {useState} from "react";
import {Empty} from "../../components/Empty.tsx";
import {Section} from "../../components/Section.tsx";
import type {MonthTotal} from "../../api/expenses.ts";
import {fmt, fmtSigned, type Expense} from "../../lib/money.ts";
import {colorOf} from "../../lib/util.ts";

const monthLabel = (ym: string) =>
    new Date(ym + "-01T00:00").toLocaleDateString(undefined, {month: "long", year: "numeric"});

const part = (d: string, opt: Intl.DateTimeFormatOptions) =>
    new Date(d + "T00:00").toLocaleDateString(undefined, opt);

// Expects newest first; groups keep that order.
function byMonth(expenses: Expense[]): [string, Expense[]][] {
    const months = new Map<string, Expense[]>();
    for (const e of expenses) months.set(e.date.slice(0, 7), [...(months.get(e.date.slice(0, 7)) ?? []), e]);
    return [...months];
}

export function ExpenseList({expenses, months, currency, loading, searching, onEdit, onDelete}: {
    expenses: Expense[]; months: MonthTotal[]; currency?: string; loading: boolean; searching?: boolean; onEdit: (e: Expense) => void; onDelete: (id: string) => void | Promise<void>
}) {
    const cur = (e: Expense) => e.group?.currency ?? currency;
    const [confirm, setConfirm] = useState<Expense | null>(null);
    const [deleting, setDeleting] = useState<ReadonlySet<string>>(new Set());
    const remove = async (id: string) => {
        setDeleting((s) => new Set(s).add(id));
        try {
            await onDelete(id);
        } finally {
            setDeleting((s) => {
                const n = new Set(s);
                n.delete(id);
                return n;
            });
        }
    };
    if (expenses.length === 0)
        return loading ? null : (
            <Section title="Expenses">
                <Empty icon={<ReceiptLongIcon fontSize="large"/>} text={searching ? "No matching expenses." : "No expenses yet. Tap “Add expense”."}/>
            </Section>
        );
    return (
        <>
            {byMonth(expenses).map(([ym, items]) => {
                const rows = months.filter((m) => m.month === ym); // a month total only makes sense in one currency
                const t = rows.length === 1 ? rows[0] : undefined;
                const monthTotal = t && `${fmt(t.spent, t.currency)}${t.received ? ` · ${fmtSigned(-t.received, t.currency)}` : ""}`;
                return (
                <Section key={ym} title={monthTotal ? `${monthLabel(ym)} · ${monthTotal}` : monthLabel(ym)}>
                    <List disablePadding>
                        {items.map((e, i) => (
                            <Box key={e.id}>
                                {i > 0 && <Divider component="li"/>}
                                <ListItem disablePadding sx={{"&:hover .actions, &:focus-within .actions": {opacity: 1}}}
                                          secondaryAction={<IconButton className="actions" size="small" edge="end" color="error" aria-label={`Delete ${e.title}`}
                                                                       sx={{"@media (hover: hover)": {opacity: 0}}}
                                                                       disabled={deleting.has(e.id)} onClick={() => setConfirm(e)}><DeleteOutlineIcon fontSize="small"/></IconButton>}>
                                <ListItemButton onClick={() => onEdit(e)} aria-label={`Edit ${e.title}`} sx={{py: 0.5, px: {xs: 1.5, sm: 2}, pr: 6}}>
                                    <Box sx={{width: 32, mr: 1.5, textAlign: "center", lineHeight: 1, color: "text.secondary"}}>
                                        <Typography variant="caption" sx={{textTransform: "uppercase"}}>{part(e.date, {month: "short"})}</Typography>
                                        <Typography component="div" fontWeight={500}>{part(e.date, {day: "numeric"})}</Typography>
                                    </Box>
                                    <ListItemText primary={e.title}
                                                  secondary={(e.group || e.tags.length > 0) && <>
                                                      {e.group && <Chip label={e.group.name} size="small" variant="outlined" sx={{mr: 0.5, mt: 0.25, height: 20, fontSize: 11, color: colorOf(e.groupId), borderColor: colorOf(e.groupId)}}/>}
                                                      {e.tags.map((t) => <Chip key={t.id} label={t.name} size="small" sx={{mr: 0.5, mt: 0.25, height: 20, fontSize: 11, color: colorOf(t.id), bgcolor: `${colorOf(t.id)}22`}}/>)}
                                                  </>}
                                                  slotProps={{primary: {noWrap: true, fontWeight: 500}, secondary: {component: "div"}}} sx={{minWidth: 0}}/>
                                    <Typography fontWeight={600} color={e.cents < 0 ? "success.main" : undefined} sx={{textAlign: "right", ml: 1, flexShrink: 0, fontVariantNumeric: "tabular-nums"}}>{fmtSigned(e.cents, cur(e))}</Typography>
                                </ListItemButton>
                                </ListItem>
                            </Box>
                        ))}
                    </List>
                </Section>
                );
            })}
            <Dialog open={!!confirm} onClose={() => setConfirm(null)}>
                <DialogTitle>Delete expense?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        “{confirm?.title}” will be permanently deleted.
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{px: 3, pb: 2}}>
                    <Button onClick={() => setConfirm(null)}>Cancel</Button>
                    <Button color="error" variant="contained" onClick={() => {
                        remove(confirm!.id);
                        setConfirm(null);
                    }}>Delete</Button>
                </DialogActions>
            </Dialog>
        </>
    );
}
