import { detectPlatform, Platform } from "./lib/detectPlatform";
import { TAK_Zip } from "./lib/interfaces";
import { AndroidTab } from "./components/tabs/AndroidTab";
import { IosTab } from "./components/tabs/IosTab";
import { WindowsTab } from "./components/tabs/WindowsTab";
import { TrackerTab } from "./components/tabs/TrackerTab";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/ui/select";
import { useEffect, useState } from "react";
import { Spinner } from "./components/ui/spinner";
import { useTranslation } from "react-i18next";

import enLang from "./locales/en.json";
import fiLang from "./locales/fi.json";
import svLang from "./locales/sv.json";

interface Props {
  data: {
    tak_zips: TAK_Zip[];
  };
}

const platformToIndex: Record<Platform, number> = {
  [Platform.Android]: 0, // ATAK
  [Platform.iOS]: 1, // ITAK
  [Platform.Windows]: 0, // ATAK
  [Platform.Tracker]: 2, // Tracker
};

const PRODUCT_SHORTNAME = "tak"

export default ({ data }: Props) => {
  const defaultPlatform = detectPlatform();
  const [platform, setPlatform] = useState<Platform>(defaultPlatform);

  const [ready, setReady] = useState(false);

  const { t, i18n } = useTranslation(PRODUCT_SHORTNAME);

  useEffect(() => {
    async function load(){
      // Load whatever languages the product supports (recommended: en/fi/sv).
      // English is the only requirement due to it being the fallback language frontend.
      i18n.addResourceBundle("en", PRODUCT_SHORTNAME, enLang)
      i18n.addResourceBundle("fi", PRODUCT_SHORTNAME, fiLang)
      i18n.addResourceBundle("sv", PRODUCT_SHORTNAME, svLang)

      await i18n.loadNamespaces(PRODUCT_SHORTNAME)
      
      setReady(true)
    }

    load()
  }, [])
  
  const getZip = (system: Platform) => data.tak_zips[platformToIndex[system]];

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div>
        <h1 className="text-2xl font-bold text-center">{t("intro.title")}</h1>
        <div className="text-muted-foreground text-center mt-2">
          <p>{t("intro.description")}</p>
        </div>
      </div>

      {data.tak_zips ? (
        <div className="mt-8 font-black">
          <p className="text-center">{t("platform.choose")}</p>
          <div className="w-full mt-2">
            <Select
              value={platform}
              onValueChange={(value) => setPlatform(value as Platform)}
            >
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
                  <img src="/ui/tak/android.svg" className="h-4 inline mr-1" />{" "}
                  / <img src="/ui/tak/apple.svg" className="h-4 inline ml-1" />{" "}
                  {t("platform.tracker")}
                </SelectItem>
              </SelectContent>
            </Select>

            <div className="mt-4">
              {platform === Platform.Android && (
                <AndroidTab zip={getZip(Platform.Android)} />
              )}
              {platform === Platform.iOS && <IosTab zip={getZip(Platform.iOS)} />}
              {platform === Platform.Windows && (
                <WindowsTab zip={getZip(Platform.Windows)} />
              )}
              {platform === Platform.Tracker && (
                <TrackerTab zip={getZip(Platform.Tracker)} />
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center w-full mt-8">
          <Spinner className="size-8 mb-4" />
          <p className="text-accent-foreground">{t("loading.user_data")}</p>
        </div>
      )}
    </div>
  );
};
