import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { Button } from "../ui/button";
import { ZipButton } from "../ZipButton";

interface Props {
  variant: string;
}

export function IosTab({ variant }: Props) {
  const { t } = useTranslation("tak");

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.ios.title")}</p>
      <div className="font-normal">
        <p>{t("tabs.ios.step1_download")}</p>
        <ZipButton zipVariant={variant} className="p-2" />
      </div>
      <div className="mt-4">
        <p className="mb-2">{t("tabs.ios.instructions_short")}</p>
        <Button asChild variant="secondary">
          {/* eslint-disable-next-line */}
          <Link to={"/ios/1" as any}>{t("tabs.ios.open_instructions")}</Link>
        </Button>
      </div>
    </div>
  );
}
