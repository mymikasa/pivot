import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi-parse.json",
  output: "src/lib/parse-api-generated",
  plugins: [
    {
      name: "@hey-api/client-axios",
      runtimeConfigPath: "./src/lib/openapi-runtime.ts",
    },
  ],
})
