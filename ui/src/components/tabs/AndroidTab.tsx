import { TAK_Zip } from "@/lib/interfaces";
import { ZipButton } from "../ZipButton";
import { useTranslation } from "react-i18next";
import { Link } from "@tanstack/react-router";
import { Button } from "../ui/button";

interface Props {
  zip: TAK_Zip;
}

export function AndroidTab({ zip }: Props) {
  const { t } = useTranslation("tak");

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.android.title")}</p>
      <div className="font-normal">
        <p>{t("tabs.android.step1_download")}</p>
        <ZipButton
          data={zip.data}
          text={zip.title}
          filename={zip.filename}
          className="p-2"
        />
      </div>
      <div className="mt-4">
        <p className="mb-2">{t("tabs.android.instructions_short")}</p>
        <Button asChild variant="secondary">
          <Link to={"/android/1" as any}>{t("tabs.android.open_instructions")}</Link>
        </Button>
      </div>
    </div>
  );
}
