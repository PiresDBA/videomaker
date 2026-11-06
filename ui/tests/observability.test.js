import { test, expect } from "@playwright/test";

test("Observabilidade + interações premium (telemetria, WS, toasts, tema, sidebar)", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("http://localhost:5173");

  await expect(page.locator(".slate .pill.ok").filter({ hasText: "API" })).toBeVisible();

  await page.locator('button.nav-item').filter({ hasText: "Atividade" }).first().click();
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".slate .pill.ok").filter({ hasText: "WS" })).toBeVisible();
  await expect(page.locator("text=Conectado (WebSocket)")).toBeVisible();
  // histórico hidratado ou placeholder — mas o painel de logs deve existir
  await expect(page.locator(".logs-panel")).toBeVisible();

  await page.locator('button.nav-item').filter({ hasText: "Diário" }).first().click({ timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".statusline").first()).toBeVisible();

  await page.locator('button').filter({ hasText: "Simulação" }).first().click();
  await expect(page.locator(".toast").first()).toContainText("Simula", { timeout: 10000 });

  await page.locator('button.nav-item').filter({ hasText: "Ajustes" }).first().click();
  await page.locator("button.chip").filter({ hasText: "Claro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light", { timeout: 5000 });
  await page.locator("button.chip").filter({ hasText: "Escuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  const before = await page.locator(".sidebar").getAttribute("class");
  expect(before).toContain("open");
  await page.locator('button[title="Fechar menu"]').click();
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
  await page.locator('button[title="Abrir menu"]').click();
  await expect(page.locator(".sidebar")).toHaveClass(/open/);

  await page.waitForTimeout(500);
  const mainCls = await page.locator(".main").evaluate((el) => getComputedStyle(el).marginLeft);
  expect(parseInt(mainCls)).toBeGreaterThan(200);

  await page.keyboard.press("Control+Enter");
  await expect(page.locator(".toast").filter({ hasText: "pipeline iniciado" }).or(
    page.locator(".toast").filter({ hasText: "antes de gerar" })
  ).first()).toBeVisible({ timeout: 8000 });

  // WS ao vivo: na página Atividade, disparar dry_run por API deve gerar logs visíveis
  await page.locator('button.nav-item').filter({ hasText: "Atividade" }).first().click();
  await page.waitForLoadState("networkidle");
  await expect(page.locator("text=Conectado (WebSocket)")).toBeVisible({ timeout: 10000 });
  await page.request.post("http://127.0.0.1:8765/api/daily/run", { data: { dry_run: true } });
  await expect(page.locator(".logs-body .log-entry").first()).toBeVisible({ timeout: 15000 });
});
