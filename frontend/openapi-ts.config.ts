import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "src/lib/api-generated",
  plugins: [
    {
      name: "@hey-api/client-axios",
      runtimeConfigPath: "./src/lib/openapi-runtime.ts",
    },
  ],
})
