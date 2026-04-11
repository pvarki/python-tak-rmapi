import { http, HttpResponse } from "msw";

const MOCK_DOMAIN = "demo.pvarki.fi";

export const handlers = [
  // TAK data packages
  http.get("/api/v1/tak-datapackages/*", () => {
    return HttpResponse.json({
      packages: [
        {
          name: "ATAK-default",
          platform: "atak",
          url: "#",
          size: "2.4MB",
        },
      ],
    });
  }),

  // TAK mission packages
  http.get("/api/v1/tak-missionpackages/*", () => {
    return HttpResponse.json({
      packages: [],
    });
  }),

  // Ephemeral download URL — matched by the proxy path used in production
  http.get(
    "/api/v1/product/proxy/tak/api/v1/tak-missionpackages/ephemeral/atak.zip",
    () => {
      return HttpResponse.json({
        ephemeral_url: `https://${MOCK_DOMAIN}/demo-not-available`,
      });
    },
  ),

  // Catch-all for any other tak proxy paths (downloads etc.)
  http.get("/api/v1/product/proxy/tak/*", () => {
    return HttpResponse.json({
      demo: true,
      message: "Downloads are not available in demo mode",
    });
  }),

  // Product description
  http.get("/api/v2/descriptions/:language", ({ params }) => {
    const lang = (params.language as string) || "en";
    const descriptions: Record<string, object> = {
      en: {
        shortname: "tak",
        title: "TAK: Team Awareness Kit",
        description: "Situational awareness system",
        component: { type: "component", ref: "tak" },
      },
      fi: {
        shortname: "tak",
        title: "TAK: Team Awareness Kit",
        description: "Tilannekuvajärjestelmä",
        component: { type: "component", ref: "tak" },
      },
      sv: {
        shortname: "tak",
        title: "TAK: Team Awareness Kit",
        description: "Situationsbildsystem",
        component: { type: "component", ref: "tak" },
      },
    };
    return HttpResponse.json(descriptions[lang] || descriptions["en"]);
  }),

  // Instructions data
  http.get("/api/v2/instructions/data/tak", () => {
    return HttpResponse.json({
      server_url: `tak.${MOCK_DOMAIN}`,
      server_port: 8089,
      protocol: "ssl",
      status: "online",
      connected_clients: 12,
    });
  }),

  // Health check
  http.get("/api/v1/healthcheck", () => {
    return HttpResponse.json({
      dns: MOCK_DOMAIN,
      version: "mock-2.0.0",
      deployment: "MOCK DEMO",
    });
  }),
];
