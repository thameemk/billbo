import {del, get, post, put, qs, type Page} from "./client.ts";
import type {Expense, Tag} from "../lib/money.ts";

// the API sends amount as a decimal string ("12.50"); the UI works in integer cents
type ApiExpense = { id: string; group_id: string; title: string; notes: string | null; amount: string; date: string; tags: Tag[]; updated_at: string; group?: { name: string; currency: string } };
const toExpense = (e: ApiExpense): Expense => ({
    id: e.id, groupId: e.group_id, title: e.title, notes: e.notes,
    cents: Math.round(Number(e.amount) * 100), date: e.date, tags: e.tags, updatedAt: e.updated_at,
    group: e.group && {name: e.group.name, currency: e.group.currency},
});

// tags are sent as names; the server creates the missing ones
export type ExpenseDraft = Omit<Expense, "id" | "updatedAt" | "group" | "tags"> & { tags: string[] };

export const listExpenses = (groupId: string | undefined, q: string, tagId: string | undefined, cursor?: string) =>
    get<Page<ApiExpense>>(`/expenses?${qs({group_id: groupId, q: q || undefined, tag_id: tagId, include: groupId ? undefined : "group", cursor})}`)
        .then((p) => ({...p, items: p.items.map(toExpense)}));

// whole-month totals for the same filters as the list, in cents; one entry per month and currency
export type MonthTotal = { month: string; currency: string; spent: number; received: number };
export const monthlyTotals = (groupId: string | undefined, q: string, tagId: string | undefined, from: string, to: string) =>
    get<{ items: { month: string; currency: string; spent: string; received: string }[] }>(`/expenses/monthly?${qs({group_id: groupId, q: q || undefined, tag_id: tagId, from, to})}`)
        .then(({items}): MonthTotal[] => items.map((r) => ({...r, spent: Math.round(Number(r.spent) * 100), received: Math.round(Number(r.received) * 100)})));

export const createExpense = (d: ExpenseDraft) =>
    post<ApiExpense>("/expenses", {
        group_id: d.groupId, title: d.title, notes: d.notes, amount: (d.cents / 100).toFixed(2), date: d.date, tags: d.tags,
    }).then(toExpense);

export const updateExpense = (id: string, d: ExpenseDraft) =>
    put<ApiExpense>(`/expenses/${id}`, {
        title: d.title, notes: d.notes, amount: (d.cents / 100).toFixed(2), date: d.date, tags: d.tags,
    }).then(toExpense);

export const deleteExpense = (id: string) => del(`/expenses/${id}`);
