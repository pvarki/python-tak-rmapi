import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

if (__USE_GLOBAL_CSS__ == true) {
  import("./index.css");
}

// Replace entire thing with response from the actual API
const SAMPLE_DATA = {
  "data": {

  }
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <div className="dark m-4">
      {/* @ts-ignore - we cant either way type check with the real ui */}
      <App data={SAMPLE_DATA.data} />
    </div>
  </React.StrictMode>,
);
