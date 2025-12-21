import { TAK_Zip } from "@/lib/interfaces";
import { ZipButton } from "../ZipButton";
import { useTranslation } from "react-i18next";
import { Link } from "@tanstack/react-router";
import { Button } from "../ui/button";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  zip: TAK_Zip;
}

interface EphemeralUrl {
  ephemeral_url: string;
}

export function AndroidTab({ zip }: Props) {
  const { t } = useTranslation("tak");
  const baseUrl = `${window.location.protocol}//${window.location.host}`;
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [takUrl, setTakUrl] = useState("");

  const handleOpenATAK = async () => {
    try {
      const response = await fetch(
        `${baseUrl}/api/v1/product/proxy/tak/api/v1/tak-missionpackages/ephemeral/atak.zip`
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json() as EphemeralUrl;
      const fullTakUrl = `tak://com.atakmap.app/import?url=${data.ephemeral_url}`;
      setTakUrl(fullTakUrl);
      setIsDialogOpen(true);
    } catch (error) {
      console.error("Error fetching ephemeral URL:", error);
      // You might want to show an error toast/notification here
    }
  };

  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">{t("tabs.android.title")}</p>
      <div className="font-normal">
        {/*<Button asChild>*/}
        {/*  /!* eslint-disable-next-line *!/*/}
        {/*  <Link*/}
        {/*    to={*/}
        {/*      `tak://com.atakmap.app/import?url=${baseUrl}/api/v1/product/proxy/tak/api/v1/proxy/client-zip/atak.zip` as any*/}
        {/*    }*/}
        {/*  >*/}
        {/*    {t("tabs.android.open_atak")}*/}
        {/*  </Link>*/}
        {/*</Button>*/}
        <Button onClick={() => void handleOpenATAK()}>
          {t("tabs.android.open_atak")}
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

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>ATAK Import URL</DialogTitle>
            <DialogDescription>
              Click the link below to open in ATAK
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <a
              href={takUrl}
              className="text-blue-600 hover:text-blue-800 underline break-all"
              onClick={() => setIsDialogOpen(false)}
            >
              {takUrl}
            </a>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}
