import { test, expect } from "@playwright/test";

test("UI Premium - Teste Completo de Todas as Páginas e Funcionalidades", async ({ page }) => {
  const response = await page.goto("http://localhost:5173");
  expect(response.status()).toBe(200);

  // PÁGINA CRIAR (página padrão)
  await expect(page.locator("h1.text-3xl")).toContainText("Criar Vídeo");
  await expect(page.locator('textarea[placeholder*="Frida e Luna"]')).toBeVisible();
  await expect(page.locator("text=Etapas do pipeline")).toBeVisible();
  await expect(page.locator("text=Gerar Vídeo")).toBeVisible();

  // PÁGINA PUBLICAR
  await page.locator('button.nav-item').filter({ hasText: "Publicar" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Publicar no YouTube");
  await expect(page.locator("h2").filter({ hasText: "Projetos disponíveis" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Ou escolher arquivo de vídeo (MP4)" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Opções de envio" })).toBeVisible();
  await expect(page.locator("text=Enviar ao YouTube")).toBeVisible();

  // PÁGINA DIÁRIO
  await page.locator('button.nav-item').filter({ hasText: "Diário" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Diário & Agendamento");
  await expect(page.locator("h2").filter({ hasText: "Executor Diário" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Calendário mensal" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Agendar novo vídeo" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Tópicos disponíveis" })).toBeVisible();

  // PÁGINA TESTES
  await page.locator('button.nav-item').filter({ hasText: "Testes" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Testes de Pipeline");
  await expect(page.locator("h2").filter({ hasText: "Modo Teste (todas as etapas)" })).toBeVisible();
  await expect(page.locator("h2").filter({ hasText: "Retomada de qualquer ponto" })).toBeVisible();
  await expect(page.locator("button").filter({ hasText: "Executar Teste Completo" })).toBeVisible();
  await expect(page.locator("button").filter({ hasText: "Retomar Execução" })).toBeVisible();

  // PÁGINA ATIVIDADE
  await page.locator('button.nav-item').filter({ hasText: "Atividade" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Atividade & Observabilidade");
  await expect(page.locator("text=Conectado (WebSocket)")).toBeVisible();

  // PÁGINA EXECUTIVO
  await page.locator('button.nav-item').filter({ hasText: "Executivo" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Painel Executivo");
  await expect(page.locator(".kpi-tile")).toHaveCount(4);

  // PÁGINA AJUSTES
  await page.locator('button.nav-item').filter({ hasText: "Ajustes" }).first().click();
  await expect(page.locator("h1.text-3xl")).toContainText("Ajustes");
  await expect(page.locator("text=Tema da interface")).toBeVisible();
});
