export const uid = () => crypto.randomUUID();
// local calendar date as YYYY-MM-DD (toISOString would give the UTC date)
export const today = (d = new Date()) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const day = (d: string) => new Date(d + "T00:00").toLocaleDateString(undefined, {
    day: "numeric",
    month: "short"
});
// stable "random" colour for a group or tag: derived from its id, so it never changes between renders or renames
const PALETTE = ["#6366f1", "#0ea5e9", "#14b8a6", "#f59e0b", "#ec4899", "#8b5cf6", "#f97316", "#22c55e"];
export const colorOf = (id: string) => PALETTE[[...id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0) % PALETTE.length];
// "YYYY-MM" shifted by n months (negative = back), across year ends
export const shiftMonth = (ym: string, n: number) => today(new Date(+ym.slice(0, 4), +ym.slice(5, 7) - 1 + n, 1)).slice(0, 7);
