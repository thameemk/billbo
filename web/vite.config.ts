import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    // app-shell precache only; API calls always go to the network
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Billbo",
        short_name: "Billbo",
        display: "standalone",
        theme_color: "#1f2937",
        background_color: "#ffffff",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
        ],
      },
      workbox: { navigateFallbackDenylist: [/^\/api/] },
    }),
  ],
});
