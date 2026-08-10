import { useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";

import { OnboardingHandler } from "../instructions/onboarding/OnboardingHandler";
import { AndroidTab } from "../tabs/AndroidTab";
import { IosTab } from "../tabs/IosTab";
import { TrackerTab } from "../tabs/TrackerTab";
import { WindowsTab } from "../tabs/WindowsTab";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

import { detectPlatform, Platform } from "@/lib/detectPlatform";

const platformToVariant: Record<Platform, string> = {
  [Platform.Android]: "atak",
  [Platform.iOS]: "itak",
  [Platform.Windows]: "atak",
  [Platform.Tracker]: "tak-tracker",
};

const PRODUCT_SHORTNAME = "tak";

export const HomePage = () => {
  const defaultPlatform = useMemo(() => detectPlatform(), []);
  const [platform, setPlatform] = useState<Platform>(defaultPlatform);

  const { t } = useTranslation(PRODUCT_SHORTNAME);

  const handlePlatformChange = useCallback((value: string) => {
    setPlatform(value as Platform);
  }, []);

  const currentTab = useMemo(() => {
    switch (platform) {
      case Platform.Android:
        return <AndroidTab variant={platformToVariant[Platform.Android]} />;
      case Platform.iOS:
        return <IosTab variant={platformToVariant[Platform.iOS]} />;
      case Platform.Windows:
        return <WindowsTab variant={platformToVariant[Platform.Windows]} />;
      case Platform.Tracker:
        return <TrackerTab variant={platformToVariant[Platform.Tracker]} />;
      default:
        return null;
    }
  }, [platform]);

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div>
        <h1 className="text-2xl font-bold text-center">{t("intro.title")}</h1>
        <div className="text-muted-foreground text-center mt-2">
          <p>{t("intro.description")}</p>
        </div>
      </div>

      <div className="mt-8 font-black">
        <p className="text-center">{t("platform.choose")}</p>
        <div className="w-full mt-2">
          <Select value={platform} onValueChange={handlePlatformChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t("platform.select_placeholder")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={Platform.Android}>
                <img src="/ui/tak/android.svg" className="h-4 inline mr-2" />{" "}
                {t("platform.android")}
              </SelectItem>
              <SelectItem value={Platform.iOS}>
                <img src="/ui/tak/apple.svg" className="h-4 inline mr-2" />{" "}
                {t("platform.ios")}
              </SelectItem>
              <SelectItem value={Platform.Windows}>
                <img src="/ui/tak/windows.svg" className="h-4 inline mr-2" />{" "}
                {t("platform.windows")}
              </SelectItem>
              <SelectItem value={Platform.Tracker}>
                <img src="/ui/tak/android.svg" className="h-4 inline mr-1" /> /{" "}
                <img src="/ui/tak/apple.svg" className="h-4 inline ml-1" />{" "}
                {t("platform.tracker")}
              </SelectItem>
            </SelectContent>
          </Select>

          <div className="mt-4">{currentTab}</div>
        </div>

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <OnboardingHandler />
        </div>
      </div>
    </div>
  );
};
