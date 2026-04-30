import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./i18n";

import {
  Outlet,
  RouterProvider,
  createRouter,
  createRootRoute,
  createRoute,
  redirect,
} from "@tanstack/react-router";

async function enableMocking() {
  if (import.meta.env.VITE_MOCK !== "true") return;
  const { worker } = await import("./mocks/browser");
  await worker.start({
    onUnhandledRequest: "bypass",
    serviceWorker: { url: "/mockServiceWorker.js" },
  });
  console.log("[MOCK] MSW enabled, TAK integration API calls are mocked");
}

const rootRoute = createRootRoute({
  component: () => (
    <>
      <Outlet />
    </>
  ),
});

const mtxRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "product/tak/$",
  component: () => {
    // Mock TAK zip data for each platform (Android/ATAK, iOS/ITAK, Tracker)
    const MOCK_TAK_ZIPS = [
      {
        title: "ATAK Package (Demo)",
        filename: "demo-atak.zip",
        data: "data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
      },
      {
        title: "iTAK Package (Demo)",
        filename: "demo-itak.zip",
        data: "data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
      },
      {
        title: "Tracker Package (Demo)",
        filename: "demo-tracker.zip",
        data: "data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
      },
    ];

    const MOCK_META = {
      theme: "default",
      callsign: "DemoUser",
    };

    return <App data={{ tak_zips: MOCK_TAK_ZIPS }} meta={MOCK_META} />;
  },
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({
      //@ts-ignore
      to: "/product/tak",
    });
  },
  component: () => <h1>Redirecting...</h1>,
});

const routeTree = rootRoute.addChildren([mtxRoute, indexRoute]);

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

if (__USE_GLOBAL_CSS__ == true) {
  import("./index.css");
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <RouterProvider router={router} />
    </React.StrictMode>,
  );
});
