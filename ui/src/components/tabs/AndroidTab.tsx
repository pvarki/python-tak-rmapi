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
  const baseUrl = `${window.location.protocol}//${window.location.host}`;

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.android.title")}</p>
      <div className="font-normal">
        <Button asChild>
          {/* eslint-disable-next-line */}
          <Link
            to={
              `tak://com.atakmap.app/import?url=${baseUrl}/api/v1/product/proxy/tak/api/v1/proxy/client-zip/atak.zip` as any
            }
          >
            {t("tabs.android.open_atak")}
          </Link>
        </Button>

        <p className="pt-8 pb-2">{t("tabs.android.open_atak_manual_note")}</p>

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
          {/* eslint-disable-next-line */}
          <Link to={"/android/1" as any}>
            {t("tabs.android.open_instructions")}
          </Link>
        </Button>
      </div>
    </div>
  );
}
