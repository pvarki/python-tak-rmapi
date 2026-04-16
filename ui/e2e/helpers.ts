import type { Page } from "@playwright/test";

export async function setLanguage(page: Page, lang: string): Promise<void> {
  await page.addInitScript((value: string) => {
    try {
      window.localStorage.setItem("language", value);
    } catch {}
  }, lang);
}

// Block onboarding showing up
export async function suppressTakOnboarding(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const originalGetItem = Storage.prototype.getItem;
    Storage.prototype.getItem = function patchedGetItem(
      key: string,
    ): string | null {
      if (/-tak-onboarding-.*-finished$/.test(key)) return "true";
      if (/-tak-onboarding-.*-steps$/.test(key)) return "[]";
      if (/-tak-onboarding-.*-session$/.test(key)) return null;
      return originalGetItem.call(this, key);
    };
  });
}

function buildTakUrlFromBase(base: string): string {
  const baseUrl = new URL(base);
  if (!baseUrl.hostname.startsWith("mtls.")) {
    baseUrl.hostname = `mtls.${baseUrl.hostname}`;
  }
  return new URL("/product/tak", baseUrl).toString();
}

export async function gotoTakRoute(page: Page): Promise<void> {
  const configuredBase =
    process.env.RM_BASE_URL || "https://localmaeher.dev.pvarki.fi:4439";

  const takUrl = buildTakUrlFromBase(configuredBase);
  await page.goto(takUrl);

  await page.getByTestId("home-page").waitFor({ state: "visible" });
}

export async function gotoHome(page: Page): Promise<void> {
  await gotoTakRoute(page);
}
