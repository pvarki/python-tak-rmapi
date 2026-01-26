import { useState, useEffect, useCallback, useRef } from "react";
import { Drawer, DrawerContent } from "@/components/ui/drawer";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronLeft, RotateCcw, ImageOff, BookOpen, Info } from "lucide-react";
import { useUserType } from "@/hooks/auth/useUserType";
import { useIsMobile } from "@/hooks/use-mobile";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import useHealthCheck from "@/hooks/helpers/useHealthcheck";
import { cn } from "@/lib/utils";

export const AndroidDownload = () => {
const { t } = useTranslation("tak");

    return (
  <div className="flex justify-center">
    <a
      href="https://play.google.com/store/apps/details?id=com.atakmap.app.civ&pli=1"
      target="_blank"
      rel="noopener noreferrer"
      className="border border-solid border-2 group inline-flex flex-col items-center gap-2 focus:outline-none"
    >
      <img
        src="/ui/tak/download-buttons/android/googleplay.png"
        width={200}
        alt={t("tabs.android.phase1.step1_desc_civ")}
        className="rounded-md cursor-pointer transition-all
                   group-hover:scale-105
                   group-hover:shadow-lg
                   focus-visible:ring-2
                   focus-visible:ring-primary-light"
      />

      <span className="text-sm font-medium text-primary-light group-hover:underline">
        {t("onboarding.android.downloadFromPlayStore") || "Download from Google Play"}
      </span>
    </a>
  </div>
);
}