import { TAK_Zip } from "./lib/interfaces";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import enLang from "./locales/en.json";
import fiLang from "./locales/fi.json";
import svLang from "./locales/sv.json";

import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
  RouterProvider,
} from "@tanstack/react-router";
import { HomePage } from "./components/routes/HomePage";
import { AndroidPhasePage } from "./components/routes/AndroidPhasePage";
import { AndroidInstructionPage } from "./components/routes/AndroidInstructionPage";
import { Spinner } from "./components/ui/spinner";
import { IosPhasePage } from "./components/routes/IosPhasePage";
import { IosInstructionPage } from "./components/routes/IosInstructionPage";
import { WindowsInstructionPage } from "./components/routes/WindowsInstructionPage";
import { WindowsPhasePage } from "./components/routes/WindowsPhasePage";

const RootLayoutComponent = () => (
  <div className="max-w-5xl mx-auto p-6">
    <Outlet />
  </div>
);

const rootRoute = createRootRoute({
  component: RootLayoutComponent,
});

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomePage,
});

//Android
const androidRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/android",
  component: AndroidInstructionPage,
});

const androidPhaseRoute = createRoute({
  getParentRoute: () => androidRoute,
  path: "$phaseId",
  component: AndroidPhasePage,
});

//Ios
const iosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/ios",
  component: IosInstructionPage,
});

const iosPhaseRoute = createRoute({
  getParentRoute: () => iosRoute,
  path: "$phaseId",
  component: IosPhasePage,
});

//Windows
const windowsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/windows",
  component: WindowsInstructionPage,
});

const windowsPhaseRoute = createRoute({
  getParentRoute: () => windowsRoute,
  path: "$phaseId",
  component: WindowsPhasePage,
});

const routeTree = rootRoute.addChildren([
  homeRoute,
  androidRoute,
  androidPhaseRoute,
  iosRoute,
  iosPhaseRoute,
  windowsPhaseRoute,
  windowsRoute,
]);

interface Props {
  data: {
    tak_zips: TAK_Zip[];
  };
}

const PRODUCT_SHORTNAME = "tak";

export default ({ data }: Props) => {
  const [ready, setReady] = useState(false);

  const { t, i18n } = useTranslation(PRODUCT_SHORTNAME);
  const router = createRouter({ routeTree, basepath: "/product/tak" });

  useEffect(() => {
    async function load() {
      // Load whatever languages the product supports (recommended: en/fi/sv).
      // English is the only requirement due to it being the fallback language frontend.
      i18n.addResourceBundle("en", PRODUCT_SHORTNAME, enLang);
      i18n.addResourceBundle("fi", PRODUCT_SHORTNAME, fiLang);
      i18n.addResourceBundle("sv", PRODUCT_SHORTNAME, svLang);

      await i18n.loadNamespaces(PRODUCT_SHORTNAME);

      setReady(true);
    }

    load();
  }, []);

  if (!ready) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spinner className="size-6" />
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  return <RouterProvider router={router} context={data} />;
};
