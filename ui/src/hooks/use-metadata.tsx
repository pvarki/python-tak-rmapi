import { createContext, useContext, ReactNode, useMemo } from "react";

export interface MetaData {
  theme: string;
  callsign: string;
}

const MetaContext = createContext<MetaData | undefined>(
  undefined,
) as React.Context<MetaData | undefined>;

export const MetadataProvider = ({
  children,
  meta,
}: {
  children: ReactNode;
  meta: MetaData;
}) => {
  const value = useMemo(() => meta, [meta.theme, meta.callsign]);

  return (
    <MetaContext.Provider value={value as MetaData}>
      {children}
    </MetaContext.Provider>
  );
};

export const useMetadata = () => {
  const context = useContext(MetaContext);
  const isMock = import.meta.env.VITE_MOCK === "true";

  if (!context && !isMock) {
    throw new Error("useMetadata must be used within a MetadataProvider");
  }

  return (
    context || {
      theme: "default",
      callsign: "Fighter01",
    }
  );
};
