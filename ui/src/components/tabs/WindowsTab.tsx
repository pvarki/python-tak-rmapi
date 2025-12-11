import { TAK_Zip } from "@/lib/interfaces";
import { ZipButton } from "../ZipButton";
import { useTranslation } from "react-i18next";
import { Link } from "@tanstack/react-router";
import { Button } from "../ui/button";

interface Props {
  zip: TAK_Zip;
}

export function WindowsTab({ zip }: Props) {
  const { t } = useTranslation("tak");

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.windows.title")}</p>
      <div className="font-normal">
        <p>{t("tabs.windows.step1_download")}</p>
        <ZipButton
          data={zip.data}
          text={zip.title}
          filename={zip.filename}
          className="p-2"
        />

          <p className="text-xs mt-2 text-muted-foreground pl-2 border-l-2 border-muted-foreground">
            {t("tabs.windows.step1_note")}
          </p>
      </div>
      <div className="mt-4">
        <p className="mb-2">{t("tabs.windows.instructions_short")}</p>
        <Button asChild variant="secondary">
          <Link to={"/windows/1" as any}>{t("tabs.windows.open_instructions")}</Link>
        </Button>
      </div>
    </div>
  );
}
