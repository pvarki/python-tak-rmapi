import { useTranslation } from "react-i18next";

import { ZipButton } from "../ZipButton";

interface Props {
  variant: string;
}

export function TrackerTab({ variant }: Props) {
  const { t } = useTranslation("tak");

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.tracker.title")}</p>
      <ol className="list-decimal list-inside space-y-4 mt-4">
        <li>
          {t("tabs.tracker.step1_download")}
          <br />
          <ZipButton zipVariant={variant} className="p-2" />
        </li>
        <li>{t("tabs.tracker.step2_install")}</li>
        <li>{t("tabs.tracker.step3_done")}</li>
      </ol>
    </div>
  );
}
