import {del, get, patch, post, qs, type Page} from "./client.ts";
import type {Group} from "../lib/money.ts";

// the list API sends totals as decimal strings; the UI works in integer cents
type ApiGroup = { id: string; name: string; currency: string; spent?: string; received?: string; expense_count?: number };
const toGroup = (g: ApiGroup): Group => ({
    id: g.id, name: g.name, currency: g.currency,
    spent: Math.round(Number(g.spent ?? 0) * 100),
    received: Math.round(Number(g.received ?? 0) * 100),
    count: g.expense_count ?? 0,
});

export const listGroups = (cursor?: string) =>
    get<Page<ApiGroup>>(`/groups?${qs({cursor})}`)
        .then((p) => ({...p, items: p.items.map(toGroup)}));

export const createGroup = (name: string, currency: string) =>
    post<ApiGroup>("/groups", {name, currency}).then(toGroup);

export const updateGroup = (id: string, d: { name: string; currency: string }) =>
    patch<ApiGroup>(`/groups/${id}`, d).then(toGroup);

export const deleteGroup = (id: string) => del(`/groups/${id}`);
