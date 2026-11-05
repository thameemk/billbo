import {Autocomplete, InputAdornment, TextField, ToggleButton, ToggleButtonGroup, Typography} from "@mui/material";
import {useState} from "react";
import {FormDialog} from "../../components/FormDialog.tsx";
import type {ExpenseDraft} from "../../api/expenses.ts";
import type {Expense} from "../../lib/money.ts";
import {today} from "../../lib/util.ts";

// Pass `expense` to edit it instead of adding a new one.
export function AddExpenseDialog({groupId, currency, expense, suggestions, onSave, onClose}: {
    groupId: string;
    expense?: Expense;
    suggestions: string[];
    currency: string;
    onSave: (e: ExpenseDraft) => void | Promise<void>;
    onClose: () => void
}) {
    const [tags, setTags] = useState<string[]>(expense?.tags.map((t) => t.name) ?? []);
    const [kind, setKind] = useState<"debit" | "credit">(expense && expense.cents < 0 ? "credit" : "debit");
    return (
        <FormDialog title={expense ? "Edit expense" : "Add expense"} submitLabel="Save" onClose={onClose}
                    onSubmit={(f) => onSave({
                        groupId, title: String(f.get("title")).trim(), notes: String(f.get("notes")).trim() || null,
                        cents: (kind === "credit" ? -1 : 1) * Math.round(Number(f.get("amount")) * 100), date: String(f.get("date")), tags,
                    })}>
            <TextField name="title" label="Title" defaultValue={expense?.title} required autoFocus/>
            <ToggleButtonGroup exclusive fullWidth size="small" color="primary" aria-label="Entry type" value={kind}
                               onChange={(_, v) => v && setKind(v)}>
                <ToggleButton value="debit">Debit</ToggleButton>
                <ToggleButton value="credit">Credit</ToggleButton>
            </ToggleButtonGroup>
            <TextField name="amount" label="Amount" type="number" defaultValue={expense && Math.abs(expense.cents) / 100} required
                       slotProps={{
                           htmlInput: {min: 0.01, step: 0.01, inputMode: "decimal"},
                           input: {startAdornment: <InputAdornment position="start">{currency}</InputAdornment>}
                       }}/>
            <TextField name="date" label="Date" type="date" defaultValue={expense?.date ?? today()} required
                       slotProps={{inputLabel: {shrink: true}}}/>
            <TextField name="notes" label="Notes" defaultValue={expense?.notes ?? ""} multiline minRows={2}
                       slotProps={{htmlInput: {maxLength: 2000}}}/>
            <Autocomplete multiple freeSolo options={suggestions} value={tags} onChange={(_, v) => setTags(v)}
                          autoSelect slotProps={{chip: {size: "small"}}}
                          renderInput={(params) => <TextField {...params} label="Tags" helperText="Type and press Enter"/>}/>
            {expense && <Typography variant="caption" color="text.secondary">
                Last edited {new Date(expense.updatedAt).toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"})}
            </Typography>}
        </FormDialog>
    );
}
