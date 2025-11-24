import { TAK_Zip } from "@/lib/interfaces";
import { ZipButton } from "../ZipButton";
import { useTranslation } from "react-i18next";

interface Props {
  zip: TAK_Zip;
}

export function WindowsTab({ zip }: Props) {
  const { t } = useTranslation("tak");

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.windows.title")}</p>
      <ol className="list-decimal list-inside space-y-4 mt-4">
        <li>
          {t("tabs.windows.step1_download")}
          <br />
          <ZipButton
            data={zip.data}
            text={zip.title}
            filename={zip.filename}
            className="p-2"
          />
          <p className="text-xs mt-2 text-muted-foreground pl-2 border-l-2 border-muted-foreground">
            {t("tabs.windows.step1_note")}
          </p>


        </li>
        <li>{t("tabs.windows.step2_install")}</li>
        <li>{t("tabs.windows.step3_done")}</li>
      </ol>
    </div>
  );
}
