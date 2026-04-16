import path from "node:path";
import { test, expect } from "@fixtures/admin";
import type { Page, TestInfo } from "@playwright/test";
import {
  SCREENSHOTS_ENABLED,
  THEME,
  LANGUAGES,
  SCREENSHOT_DIR,
  captureFullPage,
} from "@helpers/screenshots";
import { gotoTakRoute, setLanguage, suppressTakOnboarding } from "./helpers";

type PlatformName = "android" | "ios" | "windows";

const PLATFORM_SCREENSHOTS: Array<{
  name: PlatformName;
  tabTestId: string;
  downloadButtonTestId: string;
}> = [
  {
    name: "android",
    tabTestId: "tab-android",
    downloadButtonTestId: "download-package-button-android",
  },
  {
    name: "ios",
    tabTestId: "tab-ios",
    downloadButtonTestId: "download-package-button-ios",
  },
  {
    name: "windows",
    tabTestId: "tab-windows",
    downloadButtonTestId: "download-package-button-windows",
  },
];

const screenshotPath = (testInfo: TestInfo, lang: string, name: string) =>
  path.join(
    SCREENSHOT_DIR,
    THEME,
    `takintegration-${testInfo.project.name}`,
    lang,
    `${name}.png`,
  );

async function reloadWithOnboardingSuppressed(page: Page): Promise<void> {
  await suppressTakOnboarding(page);
  await page.reload();
  await expect(page.getByTestId("home-page")).toBeVisible();
}

async function selectPlatform(
  page: Page,
  platform: PlatformName,
  tabTestId: string,
): Promise<void> {
  await page.getByTestId("platform-select-trigger").click();
  await page.getByTestId(`platform-option-${platform}`).click();
  await expect(page.getByTestId(tabTestId)).toBeVisible();
}

test.describe("screenshots", () => {
  test.skip(!SCREENSHOTS_ENABLED, "set SCREENSHOTS=1 to capture screenshots");

  for (const lang of LANGUAGES) {
    test.describe(`language: ${lang}`, () => {
      test("core screenshots", async ({ page }, testInfo) => {
        await setLanguage(page, lang);

        await gotoTakRoute(page);
        await expect(page.getByTestId("home-page")).toBeVisible();
        await expect(page.getByTestId("onboarding-dialog")).toBeVisible();

        await captureFullPage(
          page,
          screenshotPath(testInfo, lang, "first-time-guide-dialog"),
        );

        await reloadWithOnboardingSuppressed(page);

        for (const platform of PLATFORM_SCREENSHOTS) {
          await selectPlatform(page, platform.name, platform.tabTestId);
          await expect(
            page.getByTestId(platform.downloadButtonTestId),
          ).toBeVisible();

          await captureFullPage(
            page,
            screenshotPath(
              testInfo,
              lang,
              `${platform.name}-package-download-tab`,
            ),
          );
        }

        await selectPlatform(page, "android", "tab-android");

        await page.getByTestId("open-atak-button").click();
        await expect(page.getByTestId("atak-dialog")).toBeVisible();
        await expect(page.getByTestId("atak-dialog-open-link")).toBeVisible();

        await captureFullPage(
          page,
          screenshotPath(testInfo, lang, "android-quick-import-popup"),
        );
      });
    });
  }
});
