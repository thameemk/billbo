export type Tag = { id: string; name: string };

export type Expense = { id: string; groupId: string; title: string; cents: number; date: string; tags: Tag[]; updatedAt: string; group?: { name: string; currency: string } };

export type Group = { id: string; name: string; currency: string; cents: number; count: number };

export const fmt = (cents: number, currency = "INR") =>
    (cents / 100).toLocaleString(undefined, {style: "currency", currency});

export const total = (expenses: Expense[], groupId?: string) =>
    expenses.reduce((s, e) => s + (groupId && e.groupId !== groupId ? 0 : e.cents), 0);
