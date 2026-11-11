import {useCallback, useEffect, useRef, useState} from "react";
import {monthlyTotals, type MonthTotal} from "../api/expenses.ts";

const nextMonth = (ym: string) => new Date(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7), 1)).toISOString().slice(0, 10);

// Whole-month totals for the months on screen only. `load` fetches the months it hasn't seen
// (or all given, with force, after a change); changing the filter resets. Skipped while searching:
// a text match can't use an index, so the totals would cost a scan of every expense.
export function useMonthTotals(groupId: string | undefined, q: string, tagId: string | undefined) {
    const key = `${groupId}|${tagId}|${q}`;
    const [got, setGot] = useState<{ key: string; rows: MonthTotal[] }>({key, rows: []});
    const rows = got.key === key ? got.rows : []; // a changed filter drops the old rows at once
    const have = useRef(new Set<string>());
    const live = useRef(key);
    useEffect(() => {
        live.current = key;
        have.current = new Set();
    }, [key]);
    const load = useCallback((months: string[], force = false) => {
        const need = force ? months : months.filter((m) => !have.current.has(m));
        if (q.trim() || !need.length) return;
        need.forEach((m) => have.current.add(m));
        const sorted = [...need].sort();
        monthlyTotals(groupId, q, tagId, `${sorted[0]}-01`, nextMonth(sorted[sorted.length - 1])).then((fresh) => {
            if (live.current === key) setGot((g) => ({key, rows: [...(g.key === key ? g.rows : []).filter((r) => !need.includes(r.month) && !fresh.some((f) => f.month === r.month)), ...fresh]}));
        }, () => need.forEach((m) => have.current.delete(m))); // retried on the next load
    }, [groupId, q, tagId, key]);
    return {rows, load};
}
