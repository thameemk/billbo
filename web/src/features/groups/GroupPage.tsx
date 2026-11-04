import AddIcon from "@mui/icons-material/Add";
import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import {Box, Fab, IconButton, InputAdornment, TextField, Typography} from "@mui/material";
import {useEffect, useState} from "react";
import {AddExpenseDialog} from "../expenses/AddExpenseDialog.tsx";
import {InfiniteScroll} from "../../components/InfiniteScroll.tsx";
import type {ExpenseDraft} from "../../api/expenses.ts";
import {ExpenseList} from "../expenses/ExpenseList.tsx";
import {fmt, total, type Expense, type Group} from "../../lib/money.ts";

export function GroupPage({g, expenses, onQuery, onAdd, onEdit, onDelete, paging, tags}: {
    g?: Group; // undefined = all expenses across groups
    expenses: Expense[]; onAdd: (e: ExpenseDraft) => void | Promise<void>; onEdit: (id: string, e: ExpenseDraft) => void | Promise<void>;
    onDelete: (id: string) => void | Promise<void>;
    onQuery: (q: string) => void; // called once typing pauses
    tags: string[];
    paging: { loadMore: () => void; retry: () => void; hasMore: boolean; loading: boolean; error: string };
}) {
    const [search, setSearch] = useState("");
    useEffect(() => {
        const t = setTimeout(() => onQuery(search.trim()), 300);
        return () => clearTimeout(t);
    }, [search, onQuery]);
    const [adding, setAdding] = useState(false);
    const [editing, setEditing] = useState<Expense>();
    const mine = (g ? expenses.filter((e) => e.groupId === g.id) : [...expenses]).sort((a, b) => b.date.localeCompare(a.date));
    return (
        <>
            {g && <Box sx={{mb: 2}}>
                <Typography variant="body2" color="text.secondary">Total spent</Typography>
                <Typography variant="h4" fontWeight={700}>{fmt(total(mine), g.currency)}</Typography>
            </Box>}
            <TextField size="small" fullWidth placeholder="Search title or tag" value={search}
                       onChange={(e) => setSearch(e.target.value)} sx={{mb: 2, "& .MuiOutlinedInput-root": {bgcolor: "background.paper", borderRadius: 999}}}
                       slotProps={{
                           htmlInput: {"aria-label": "Search expenses"},
                           input: {
                               startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small"/></InputAdornment>,
                               endAdornment: search && <InputAdornment position="end">
                                   <IconButton size="small" aria-label="Clear search" onClick={() => setSearch("")}><ClearIcon fontSize="small"/></IconButton>
                               </InputAdornment>
                           }
                       }}/>
            <ExpenseList searching={!!search.trim()} expenses={mine} currency={g?.currency} loading={paging.loading || !!paging.error} onEdit={setEditing} onDelete={onDelete}/>
            <InfiniteScroll onMore={paging.loadMore} onRetry={paging.retry} hasMore={paging.hasMore} loading={paging.loading} count={expenses.length} error={paging.error}/>
            <Box sx={{height: 72}}/>
            {g && <Fab color="primary" variant="extended" onClick={() => setAdding(true)}
                 sx={{position: "fixed", right: 24, bottom: 24}}>
                <AddIcon sx={{mr: 1}}/> Add expense
            </Fab>}
            {g && adding && <AddExpenseDialog suggestions={tags} groupId={g.id} currency={g.currency} onClose={() => setAdding(false)} onSave={async (e) => {
                await onAdd(e);
                setAdding(false);
            }}/>}
            {editing && <AddExpenseDialog suggestions={tags} groupId={editing.groupId} currency={editing.group?.currency ?? g?.currency ?? "INR"} expense={editing} onClose={() => setEditing(undefined)} onSave={async (e) => {
                await onEdit(editing.id, e);
                setEditing(undefined);
            }}/>}
        </>
    );
}
