import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { TanStackRouterVite } from "@tanstack/router-plugin/vite"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss(), TanStackRouterVite()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/api/v1/parse": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/v1/kb": {
        target: "http://localhost:8082",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:8081",
        changeOrigin: true,
      },
    },
  },
})
