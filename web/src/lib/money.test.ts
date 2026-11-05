import test from "node:test";
import assert from "node:assert/strict";
import {adjustTotals, totals, type Expense, type Group} from "./money.ts";

const e = (cents: number): Expense => ({id: "x", groupId: "a", title: "", notes: null, cents, date: "2026-01-01", tags: [], updatedAt: ""});

test("totals keeps debits and credits apart", () => {
    assert.deepEqual(totals([e(1050), e(250), e(-999)]), {spent: 1300, received: 999});
    assert.deepEqual(totals([]), {spent: 0, received: 0});
});

test("adjustTotals", () => {
    const g: Group = {id: "a", name: "", currency: "INR", spent: 1000, received: 200, count: 2};
    const stats = ({spent, received, count}: Group) => [spent, received, count];
    assert.deepEqual(stats(adjustTotals(g, 0, 500, 1)), [1500, 200, 3]); // add a debit
    assert.deepEqual(stats(adjustTotals(g, -200, 0, -1)), [1000, 0, 1]); // delete a credit
    assert.deepEqual(stats(adjustTotals(g, 300, 400)), [1100, 200, 2]); // edit a debit
    assert.deepEqual(stats(adjustTotals(g, 300, -300)), [700, 500, 2]); // debit becomes credit
});
