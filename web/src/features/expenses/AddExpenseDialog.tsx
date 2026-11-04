import {Autocomplete, InputAdornment, TextField, Typography} from "@mui/material";
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
    return (
        <FormDialog title={expense ? "Edit expense" : "Add expense"} submitLabel="Save" onClose={onClose}
                    onSubmit={(f) => onSave({
                        groupId, title: String(f.get("title")).trim(),
                        cents: Math.round(Number(f.get("amount")) * 100), date: String(f.get("date")), tags,
                    })}>
            <TextField name="title" label="Title" defaultValue={expense?.title} required autoFocus/>
            <TextField name="amount" label="Amount" type="number" defaultValue={expense && expense.cents / 100} required
                       slotProps={{
                           htmlInput: {min: 0.01, step: 0.01, inputMode: "decimal"},
                           input: {startAdornment: <InputAdornment position="start">{currency}</InputAdornment>}
                       }}/>
            <TextField name="date" label="Date" type="date" defaultValue={expense?.date ?? today()} required
                       slotProps={{inputLabel: {shrink: true}}}/>
            <Autocomplete multiple freeSolo options={suggestions} value={tags} onChange={(_, v) => setTags(v)}
                          autoSelect slotProps={{chip: {size: "small"}}}
                          renderInput={(params) => <TextField {...params} label="Tags" helperText="Type and press Enter"/>}/>
            {expense && <Typography variant="caption" color="text.secondary">
                Last edited {new Date(expense.updatedAt).toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"})}
            </Typography>}
        </FormDialog>
    );
}
