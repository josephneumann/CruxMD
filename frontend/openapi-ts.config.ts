import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  // FastAPI exposes OpenAPI schema at /openapi.json by default
  input: "http://localhost:8000/openapi.json",
  output: {
    path: "./lib/generated",
  },
  plugins: [
    // Generate TypeScript types from OpenAPI schemas
    {
      name: "@hey-api/typescript",
      enums: "javascript", // JavaScript enums are more tree-shakeable than TS enums
    },
    // Generate SDK with tree-shakeable API functions
    "@hey-api/sdk",
  ],
});
