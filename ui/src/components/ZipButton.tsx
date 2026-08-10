import { Button } from "./ui/button";

import useHealthCheck from "@/hooks/helpers/useHealthcheck";

interface Props extends React.ComponentProps<typeof Button> {
  zipVariant: string;
}

export function ZipButton({ zipVariant, ...other }: Props) {
  const { deployment } = useHealthCheck();

  const title = deployment
    ? `${deployment}_${zipVariant}.zip`
    : `${zipVariant}.zip`;

  const handleDownload = () => {
    try {
      const link = document.createElement("a");
      link.href = `/api/v1/product/proxy/tak/api/v1/tak-missionpackages/client-zip/${zipVariant}.zip`;
      link.click();
    } catch (err) {
      console.error("Error downloading file:", err);
    }
  };

  return (
    <Button onClick={handleDownload} {...other}>
      {title}
    </Button>
  );
}
