import test from "node:test";
import assert from "node:assert/strict";
import {shiftMonth} from "./util.ts";

test("shiftMonth crosses year ends", () => {
    assert.equal(shiftMonth("2026-01", -1), "2025-12");
    assert.equal(shiftMonth("2026-12", 1), "2027-01");
    assert.equal(shiftMonth("2026-11", 0), "2026-11");
});
