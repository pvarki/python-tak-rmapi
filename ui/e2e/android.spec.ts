import { test, expect } from "@fixtures/admin";
import {
  gotoProductRoute,
  setLanguage,
  suppressProductOnboarding,
} from "@helpers/product";

test.describe("android flow", () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, "en");
    await suppressProductOnboarding(page, "tak");

    await gotoProductRoute(page, "tak");
    await page.getByTestId("platform-select-trigger").click();
    await page.getByTestId("platform-option-android").click();
    await expect(page.getByTestId("tab-android")).toBeVisible();
  });

  test("android quick-import flow works", async ({ page }) => {
    await expect(
      page.getByTestId("download-package-button-android"),
    ).toBeVisible();
    await expect(page.getByTestId("open-atak-button")).toBeVisible();

    await page.getByTestId("open-atak-button").click();

    await expect(page.getByTestId("atak-dialog")).toBeVisible();
    const deepLink = page.getByTestId("atak-dialog-open-link");
    await expect(deepLink).toBeVisible();
    await expect(deepLink).toHaveAttribute(
      "href",
      /^tak:\/\/com\.atakmap\.app\/import\?url=/,
    );
  });
});
