import { TAK_Zip } from "@/lib/interfaces";
import { ZipButton } from "../ZipButton";

interface Props {
  zip: TAK_Zip;
}

export function WindowsTab({ zip }: Props) {
  return (
    <div className="mt-4">
      <p className="text-lg font-semibold">WinTAK Package Installation</p>
      <ol className="list-decimal list-inside space-y-4 mt-4">
        <li>
          Download the zip package:
          <br />
          <ZipButton
            data={zip.data}
            text={zip.title}
            filename={zip.filename}
            className="p-2"
          />
        </li>
        <li>Install the package</li>
        <li>Done, WinTAK is ready to use.</li>
      </ol>
    </div>
  );
}
