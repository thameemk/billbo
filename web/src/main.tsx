import {createRoot} from "react-dom/client";
import {registerSW} from "virtual:pwa-register";
import App from "./App.tsx";

// reload onto a new version as soon as it is installed; re-check hourly for PWAs left open
registerSW({
    immediate: true,
    onRegisteredSW: (_, r) => r && setInterval(() => r.update(), 60 * 60 * 1000),
});

createRoot(document.getElementById("root")!).render(<App/>);
