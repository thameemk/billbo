// Captures the web (1440px) and iPhone 17 (402x874 @3x) screenshots for the README/website.
// Creates a throwaway demo account + sample data on every run, so run it against a LOCAL dev
// stack only (needs ALLOW_SIGNUP=true on the backend). Uses your installed Google Chrome (macOS path below).
//
//   cd scripts && npm i --no-save playwright-core
//   node screenshots.mjs ../docs/images        # output dir must exist
//
// API/WEB below default to the docker-compose ports; edit if yours differ.
import { chromium } from "playwright-core";
import crypto from "node:crypto";

const API = "http://localhost:9000/api/v1";
const WEB = "http://localhost:9001";
const OUT = process.argv[2];
const email = `demo${Date.now()}@example.net`; // unique per run, so reruns never collide
const password = crypto.randomBytes(12).toString("hex"); // throwaway, never printed

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const ctx = await browser.newContext({
  viewport: { width: 402, height: 874 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Mobile/15E148 Safari/604.1",
});
const req = ctx.request;
const j = async (m, p, data) => {
  const r = await req.fetch(API + p, { method: m, data, headers: { Origin: WEB } });
  if (!r.ok()) throw new Error(`${m} ${p} ${r.status()} ${await r.text()}`);
  return r.status() === 204 ? null : r.json();
};

await j("POST", "/users", { display_name: "Demo User", email, password });
await j("POST", "/auth/login", { email, password });

let seed = 7;
const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
const ri = (a, b) => Math.floor(a + rnd() * (b - a + 1));
const today = new Date("2026-11-14");
const dstr = (n) => { const d = new Date(today); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };
const G = {
  Household: [["Groceries","Weekly vegetables and fruit",["food","essentials"],600,2200,4],["Electricity bill","Monthly bill",["utilities","bills"],1400,3200,3],["Internet","Fiber broadband",["utilities","bills"],799,799,3],["Cooking gas",null,["essentials"],950,950,2],["House cleaning","Monthly help",["essentials"],1500,1500,3]],
  "Eating Out": [["Dinner with friends","Biryani place",["food","friends"],900,2600,4],["Coffee",null,["food","coffee"],150,420,5],["Lunch at office",null,["food"],180,380,5],["Weekend brunch","New cafe",["food","friends"],700,1800,3]],
  Subscriptions: [["Music streaming","Family plan",["entertainment","bills"],179,179,4],["Video streaming",null,["entertainment","bills"],499,499,4],["Cloud storage","200 GB",["bills"],219,219,4]],
};
for (const [name, items] of Object.entries(G)) {
  const g = await j("POST", "/groups", { name, currency: "INR" });
  for (const [title, notes, tags, lo, hi, cnt] of items)
    for (let i = 0; i < cnt; i++) {
      const day = /Music|Video|Cloud|Internet|Electricity|cleaning/.test(title) ? i * 30 + ri(0, 5) : ri(0, 120);
      await j("POST", "/expenses", { title, notes, amount: `${ri(lo, hi)}.${["00","50","25"][ri(0,2)]}`, date: dstr(day), tags, group_id: g.id });
    }
  if (name === "Eating Out")
    await j("POST", "/expenses", { title: "Split refund", notes: "Friend paid back", amount: "-1000.00", date: dstr(6), tags: ["friends"], group_id: g.id });
}

// the session cookie is already in ctx; open the app
const page = await ctx.newPage();
const shot = async (n) => { await page.waitForTimeout(700); await page.screenshot({ path: `${OUT}/${n}.png` }); console.log("saved", n); };
// The group header's Spent/Received are blurred until clicked (components/Redacted.tsx).
// Click the real amount elements and re-check, since a late data load can re-blur them.
const unblur = async (p, touch) => {
  const amounts = p.getByText(/^₹[\d,]+\.\d\d$/);
  await amounts.nth(1).waitFor(); // Spent + Received come before any list row
  await p.waitForLoadState("networkidle");
  for (const i of [0, 1]) {
    const el = amounts.nth(i);
    for (let k = 0; k < 4 && (await el.evaluate((e) => getComputedStyle(e).filter)) !== "none"; k++) {
      await (touch ? el.tap() : el.click());
      await p.waitForTimeout(400);
    }
    if ((await el.evaluate((e) => getComputedStyle(e).filter)) !== "none") throw new Error(`amount ${i} still blurred`);
  }
};

await page.goto(WEB);
try {
  const dash = page.getByText("Total spent");
  const login = page.getByLabel(/email/i);
  await dash.or(login).first().waitFor({ timeout: 15000 });
  if (await login.isVisible()) {
    // API-set cookie didn't carry over; sign in through the real form instead
    await login.fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole("button", { name: /log ?in|sign ?in/i }).click();
  }
  await dash.waitFor({ timeout: 15000 });
} catch (e) {
  await page.screenshot({ path: `${OUT}/debug.png` });
  console.log("DEBUG page text:", (await page.locator("body").innerText()).slice(0, 600));
  throw e;
}
await shot("mobile_home");

await page.mouse.click(32, 32);
await page.waitForTimeout(400);
await shot("mobile_menu");

await page.locator(".MuiDrawer-modal").getByText("Household", { exact: true }).click();
await unblur(page, true);
await shot("mobile_group_listing");

// add-expense dialog (opened and filled, never submitted)
const openAdd = async (p) => {
  await p.getByRole("button", { name: /add expense/i }).click();
  await p.waitForTimeout(600);
  try {
    await p.getByLabel(/title/i).first().fill("Weekly groceries", { timeout: 3000 });
    await p.getByLabel(/amount/i).first().fill("1850.50", { timeout: 3000 });
  } catch { console.log("could not prefill add-expense form; capturing empty"); }
};
await openAdd(page);
await shot("mobile_add_expense");
await page.keyboard.press("Escape");
await page.waitForTimeout(400);

await page.mouse.click(32, 32);
await page.waitForTimeout(400);
await page.locator(".MuiDrawer-modal").getByText("food", { exact: true }).click();
await page.getByPlaceholder(/search/i).waitFor();
await shot("mobile_tag_listing");

// ---- desktop: add-expense dialog at 1440px (same size as the other web shots) ----
const dctx = await browser.newContext({ viewport: { width: 1440, height: 723 } });
const dp = await dctx.newPage();
await dp.goto(WEB);
await dp.getByLabel(/email/i).fill(email);
await dp.getByLabel(/password/i).fill(password);
await dp.getByRole("button", { name: /log ?in|sign ?in/i }).click();
await dp.getByText("Total spent").waitFor();
const wshot = async (n) => {
  await dp.mouse.move(1400, 650); // park the cursor on blank space
  await dp.waitForTimeout(700);
  await dp.screenshot({ path: `${OUT}/${n}.png` });
  console.log("saved", n);
};
await wshot("web_home");
// demo account has <=3 groups, so only the tags card has a "View all" link
await dp.getByText(/view all/i).first().click();
await wshot("web_home_tags_expanded");

await dp.locator("nav").getByText("food", { exact: true }).click();
await dp.getByPlaceholder(/search/i).waitFor();
await wshot("web_tag_listing");

await dp.locator("nav").getByText("Household", { exact: true }).click();
await unblur(dp, false);
await wshot("web_group_listing");

await openAdd(dp);
await wshot("web_add_expense");

await browser.close();
