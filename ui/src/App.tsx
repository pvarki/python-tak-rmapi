import { detectOS, OS } from "./lib/detectOs";
import { TAK_Zip } from "./lib/interfaces";
import { AndroidTab } from "./components/tabs/AndroidTab";
import { IosTab } from "./components/tabs/IosTab";
import { WindowsTab } from "./components/tabs/WindowsTab";
import { TrackerTab } from "./components/tabs/TrackerTab";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/ui/select";
import { useState } from "react";
import { Spinner } from "./components/ui/spinner";

interface Props {
  data: {
    tak_zips: TAK_Zip[];
  };
}

const osToIndex: Record<OS, number> = {
  [OS.Android]: 0, // ATAK
  [OS.iOS]: 1, // ITAK
  [OS.Windows]: 0, // ATAK
  [OS.Tracker]: 2, // Tracker
};

export default ({ data }: Props) => {
  const defaultOS = detectOS();
  const [selectedOS, setSelectedOS] = useState<OS>(defaultOS);

  const getZip = (system: OS) => data.tak_zips[osToIndex[system]];

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div>
        <h1 className="text-2xl font-bold text-center">TAK</h1>
        <div className="text-muted-foreground text-center mt-2">
          <p>
            TAK (Team Awareness Kit): A GPS-enabled platform for real-time
            tracking of friendly forces, sharing observations, and receiving
            command updates through a centralized Recon Feed.
          </p>
        </div>
      </div>

      {data.tak_zips ? (
        <div className="mt-8 font-black">
          <p className="text-center">Choose your platform</p>
          <div className="w-full mt-2">
            <Select
              value={selectedOS}
              onValueChange={(value) => setSelectedOS(value as OS)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={OS.Android}>
                  <img src="/ui/tak/android.svg" className="h-4 inline mr-2" />{" "}
                  ATAK
                </SelectItem>
                <SelectItem value={OS.iOS}>
                  <img src="/ui/tak/apple.svg" className="h-4 inline mr-2" />{" "}
                  iTAK
                </SelectItem>
                <SelectItem value={OS.Windows}>
                  <img src="/ui/tak/windows.svg" className="h-4 inline mr-2" />{" "}
                  WinTAK
                </SelectItem>
                <SelectItem value={OS.Tracker}>
                  <img src="/ui/tak/android.svg" className="h-4 inline mr-1" />{" "}
                  / <img src="/ui/tak/apple.svg" className="h-4 inline ml-1" />{" "}
                  TAK Tracker
                </SelectItem>
              </SelectContent>
            </Select>

            <div className="mt-4">
              {selectedOS === OS.Android && (
                <AndroidTab zip={getZip(OS.Android)} />
              )}
              {selectedOS === OS.iOS && <IosTab zip={getZip(OS.iOS)} />}
              {selectedOS === OS.Windows && (
                <WindowsTab zip={getZip(OS.Windows)} />
              )}
              {selectedOS === OS.Tracker && (
                <TrackerTab zip={getZip(OS.Tracker)} />
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center w-full mt-8">
          <Spinner className="size-8 mb-4" />
          <p className="text-accent-foreground">Loading user data...</p>
        </div>
      )}
    </div>
  );
};
