export type Tag = { id: string; name: string };

// cents is signed: positive = debit, negative = credit
export type Expense = { id: string; groupId: string; title: string; notes: string | null; cents: number; date: string; tags: Tag[]; updatedAt: string; group?: { name: string; currency: string } };

// spent and received are both positive cents
export type Group = { id: string; name: string; currency: string; spent: number; received: number; count: number };

export const fmt = (cents: number, currency = "INR") =>
    (cents / 100).toLocaleString(undefined, {style: "currency", currency});

// a credit reads as "+₹5.00": a plain fmt would show it as "-₹5.00"
export const fmtSigned = (cents: number, currency = "INR") =>
    cents < 0 ? `+${fmt(-cents, currency)}` : fmt(cents, currency);

export const totals = (expenses: Expense[]) => ({
    spent: expenses.reduce((s, e) => s + Math.max(e.cents, 0), 0),
    received: expenses.reduce((s, e) => s + Math.max(-e.cents, 0), 0),
});

// move a group's totals from one signed amount to another; 0 means none, for adds and deletes
export const adjustTotals = (g: Group, from: number, to: number, count = 0): Group => ({
    ...g,
    spent: g.spent - Math.max(from, 0) + Math.max(to, 0),
    received: g.received - Math.max(-from, 0) + Math.max(-to, 0),
    count: g.count + count,
});
