import { test, expect } from "@fixtures/admin";
import { gotoHome, setLanguage, suppressTakOnboarding } from "./helpers";

type PlatformExpectation = {
  platform: "android" | "ios" | "windows" | "tracker";
  tabTestId: string;
  downloadButtonTestId: string;
};

const PLATFORM_EXPECTATIONS: PlatformExpectation[] = [
  {
    platform: "android",
    tabTestId: "tab-android",
    downloadButtonTestId: "download-package-button-android",
  },
  {
    platform: "ios",
    tabTestId: "tab-ios",
    downloadButtonTestId: "download-package-button-ios",
  },
  {
    platform: "windows",
    tabTestId: "tab-windows",
    downloadButtonTestId: "download-package-button-windows",
  },
  {
    platform: "tracker",
    tabTestId: "tab-tracker",
    downloadButtonTestId: "download-package-button-tracker",
  },
];

test.describe("home page", () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, "en");
    await suppressTakOnboarding(page);

    await gotoHome(page);
  });

  test("renders home and supports platform switching", async ({ page }) => {
    await expect(page.getByTestId("home-page")).toBeVisible();
    await expect(page.getByTestId("platform-select-trigger")).toBeVisible();
    await expect(page.getByTestId("home-loading")).toHaveCount(0);

    const tabRoot = page.locator(
      "[data-testid='tab-android'], [data-testid='tab-ios'], [data-testid='tab-windows'], [data-testid='tab-tracker']",
    );

    await expect(tabRoot).toBeVisible();
    await expect(
      page.locator(
        "[data-testid='download-package-button-android'], [data-testid='download-package-button-ios'], [data-testid='download-package-button-windows'], [data-testid='download-package-button-tracker']",
      ),
    ).toBeVisible();

    for (const {
      platform,
      tabTestId,
      downloadButtonTestId,
    } of PLATFORM_EXPECTATIONS) {
      await page.getByTestId("platform-select-trigger").click();
      await page.getByTestId(`platform-option-${platform}`).click();

      await expect(page.getByTestId(tabTestId)).toBeVisible();
      await expect(page.getByTestId(downloadButtonTestId)).toBeVisible();
    }
  });
});
