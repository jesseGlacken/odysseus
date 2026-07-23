#!/usr/bin/env node
/**
 * Generate typed TypeScript client from the OpenAPI schema.
 *
 * 1. Reads openapi.json from packages/contracts/
 * 2. Runs openapi-typescript to generate schema.d.ts
 * 3. Writes src/generated/client.ts with createClient<paths>
 */
import { execFileSync } from 'child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// When run via Nx (cwd = packages/client-sdk) or node from repo root, resolve
// paths relative to this script, not the CWD.
const repoRoot = resolve(__dirname, '../..');
const schemaPath = resolve(repoRoot, 'packages/contracts/openapi.json');
const outDir = resolve(__dirname, 'src/generated');
const schemaOut = resolve(outDir, 'schema.d.ts');
const clientOut = resolve(outDir, 'client.ts');

// Ensure the schema exists
let schema;
try {
  schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));
} catch (err) {
  console.error('Failed to read OpenAPI schema. Run contracts:generate first.');
  console.error(err.message);
  process.exit(1);
}

console.log(`Generating TypeScript types from schema (${Object.keys(schema.paths).length} paths)...`);

// Generate schema types
mkdirSync(outDir, { recursive: true });

try {
  execFileSync('npx', ['openapi-typescript', schemaPath, '-o', schemaOut], {
    encoding: 'utf-8',
    stdio: 'inherit',
  });
  console.log(`  -> ${schemaOut}`);
} catch (err) {
  console.error('Failed to generate schema types:', err.message);
  process.exit(1);
}

// Write the client wrapper
const clientCode = `/**
 * Typed API client for the Odysseus API.
 * Generated from packages/contracts/openapi.json — do not edit by hand.
 */
import createClient from "openapi-fetch";
import type { paths } from "./schema.d.ts";

export const apiClient = createClient<paths>({ baseUrl: "/api" });

export type { paths };
`;

writeFileSync(clientOut, clientCode);
console.log(`  -> ${clientOut}`);
console.log('Client SDK generated successfully.');
