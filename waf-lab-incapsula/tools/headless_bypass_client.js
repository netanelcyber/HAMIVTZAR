// Headless-browser bypass: instead of reverse-engineering the WAF's
// challenge algorithm (see crack_cipher_client.py), just load the page in
// a real Chromium instance so the challenge JS executes exactly as the WAF
// expects, then read whatever cookie/content that leaves us with.
//
// This build of headless Chromium sends "HeadlessChrome" in its UA string,
// which the lab WAF blocks outright on signature alone -- the same problem
// real headless-browser scraping runs into. The fix mirrors what real
// stealth-headless setups do: override the User-Agent to a normal Chrome
// string and patch `navigator.webdriver` (which Playwright/automation
// leaves as `true`) back to `undefined` via an init script, so the page's
// own JS challenge sees an ordinary-looking browser and runs normally.
//
// Usage:
//   NODE_PATH=/opt/node22/lib/node_modules node headless_bypass_client.js http://localhost:8080/

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

async function main() {
  const url = process.argv[2] || "http://localhost:8080/";
  const browser = await chromium.launch({
    executablePath: "/opt/pw-browsers/chromium",
    headless: true,
  });
  const context = await browser.newContext({
    locale: "en-US",
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
  });
  const page = await context.newPage();

  console.log(`[1] navigating to ${url}`);
  await page.goto(url, { waitUntil: "networkidle" });

  // The challenge page sets a cookie then calls location.reload(); give it
  // a moment to settle if we happened to land mid-challenge.
  await page.waitForTimeout(500);
  const title = await page.title();
  const bodyText = await page.evaluate(() => document.body.innerText);

  if (/checking your browser/i.test(bodyText)) {
    console.log("[2] still on challenge page, waiting for JS reload...");
    await page.waitForTimeout(1000);
  }

  const finalText = await page.evaluate(() => document.body.innerText);
  const cookies = await context.cookies();

  console.log(`[3] final title: ${title}`);
  console.log(`[4] final body: ${finalText.slice(0, 300)}`);
  console.log(
    "[5] cookies set:",
    cookies.map((c) => c.name).join(", ")
  );

  const evidenceDir = path.join(__dirname, "..", "evidence");
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(
    path.join(evidenceDir, "headless_bypass_result.json"),
    JSON.stringify(
      { url, title, finalText: finalText.slice(0, 500), cookieNames: cookies.map((c) => c.name) },
      null,
      2
    )
  );

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
