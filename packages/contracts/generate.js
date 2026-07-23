#!/usr/bin/env node
/**
 * Generate OpenAPI schema from the FastAPI app.
 *
 * Usage: node generate.js
 *
 * 1. Spawns uv run python in apps/api/ to dump app.openapi()
 * 2. Writes the JSON to packages/contracts/openapi.json
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const apiDir = path.resolve(__dirname, '../../apps/api');
const outputPath = path.resolve(__dirname, 'openapi.json');

const script = `
import sys, os, json, logging
os.chdir('src')
sys.path.insert(0, '.')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
logging.disable(logging.CRITICAL)

from app import app
schema = app.openapi()
schema['info']['title'] = 'Odysseus API'
print(json.dumps(schema, indent=2))
`.trim();

console.log('Generating OpenAPI schema from FastAPI app...');
try {
  // Write the Python script to a temp file to avoid shell-escaping issues
  const scriptPath = path.join(__dirname, '.generate_schema.py');
  fs.writeFileSync(scriptPath, script);

  const result = execSync(`uv run python ${scriptPath}`, {
    cwd: apiDir,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'pipe'],
    maxBuffer: 10 * 1024 * 1024,
    timeout: 30000,
  });

  // Validate JSON
  JSON.parse(result);

  fs.writeFileSync(outputPath, result);
  const stats = fs.statSync(outputPath);
  const schema = JSON.parse(result);
  console.log(`Generated ${(stats.size / 1024).toFixed(1)} KB schema with ${Object.keys(schema.paths).length} paths`);

  // Clean up temp script
  fs.unlinkSync(scriptPath);
} catch (err) {
  console.error('Failed to generate OpenAPI schema:', err.message);
  process.exit(1);
}
