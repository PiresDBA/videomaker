import { test, expect } from "@playwright/test";

test.describe("Painel Executivo", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:5173");
    await page.waitForLoadState("networkidle");
    const sidebar = page.locator(".sidebar");
    const isOpen = await sidebar.evaluate(el => el.classList.contains("open")).catch(() => false);
    if (!isOpen) {
      const hamburger = page.locator('[aria-label="menu"], button:has(svg.lucide-menu), .sidebar-toggle').first();
      await hamburger.click().catch(() => {});
      await page.waitForTimeout(300);
    }
  });

test("renderiza KPI tiles, gauges, waterfall, sparkline, countdown e botão de stop", async ({ page }) => {
    const errors = [];
    const networkErrors = [];
    page.on("console", msg => { if (msg.type() === "error") errors.push(msg.text()); });
    page.on("pageerror", err => errors.push(err.message));
    page.on("requestfailed", req => networkErrors.push(`${req.url()} - ${req.failure()?.errorText}`));
    page.on("response", resp => {
      if (resp.url().includes("/api/telemetry")) {
        console.log(`Telemetry API: ${resp.status()} ${resp.url()}`);
      }
    });

    await page.locator('button.nav-item').filter({ hasText: "Executivo" }).first().click();
    await page.waitForTimeout(3000);
    
    const heading = page.locator("main h1").first();
    await expect(heading).toContainText("Painel Executivo");
    console.log("Captured JS Errors:", errors);
    console.log("Network Errors:", networkErrors);
    if (errors.length) console.log("JS Errors:", errors);

    // Wait for KPI tiles to appear (they load async)
    await page.waitForSelector(".kpi-tile", { timeout: 15000 }).catch(() => {});
    
    const kpiTiles = page.locator(".kpi-tile");
    await expect(kpiTiles).toHaveCount(4);

    await expect(kpiTiles.nth(0)).toContainText("Projetos");
    await expect(kpiTiles.nth(1)).toContainText("Concluídos");
    await expect(kpiTiles.nth(2)).toContainText("Tempo médio");
    await expect(kpiTiles.nth(3)).toContainText("Próximo disparo");

    const gauges = page.locator(".gauge-wrap");
    await expect(gauges).toHaveCount(10);

    await expect(page.locator(".waterfall")).toBeVisible();
    await expect(page.locator(".sparkline-svg")).toBeVisible();

    const countdownTile = kpiTiles.nth(3);
    const countdownText = await countdownTile.locator(".kpi-value").textContent();
    await expect(countdownText?.trim()).toMatch(/^(\d{2}:\d{2}|—|agora)$/);

    const stopAgentBtn = page.locator('button:has-text("Parar agente")');
    await expect(stopAgentBtn).toBeTruthy();

    const requeueBtn = page.locator('button:has-text("Recolocar na fila")');
    await expect(requeueBtn).toBeTruthy();

    await expect(page.locator("text=Logs ao vivo")).toBeVisible();
  });

  test("navegação entre páginas não quebra", async ({ page }) => {
    await page.locator('button.nav-item').filter({ hasText: "Executivo" }).first().click();
    await page.waitForTimeout(800);
    const heading1 = page.locator("main h1").first();
    await expect(heading1).toContainText("Painel Executivo");

    await page.locator('button.nav-item').filter({ hasText: "Atividade" }).first().click();
    await page.waitForTimeout(800);
    const heading2 = page.locator("main h1").first();
    await expect(heading2).toContainText("Atividade & Observabilidade");

    await page.locator('button.nav-item').filter({ hasText: "Executivo" }).first().click();
    await page.waitForTimeout(800);
    const heading3 = page.locator("main h1").first();
    await expect(heading3).toContainText("Painel Executivo");
  });
});