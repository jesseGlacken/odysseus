#!/usr/bin/env node
/**
 * Generate OpenAPI schema from the FastAPI app.
 *
 * Usage: node generate.js
 *
 * 1. Spawns uv run python in apps/api/ to dump app.openapi()
 * 2. Writes the JSON to packages/contracts/openapi.json
 *
 * Note: this script reaches into apps/api/ for code generation.
 * The app owns the schema; this package is the publishing target.
 * See ADR-0001 §2 and M7 in the review notes.
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const apiDir = path.resolve(__dirname, '../../apps/api');
const outputPath = path.resolve(__dirname, 'openapi.json');

const script = `
import sys, os, json
os.chdir('src')
sys.path.insert(0, '.')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

# Suppress only noisy startup logs; real errors go to stderr
import logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('huggingface_hub').setLevel(logging.WARNING)

try:
    from app import app
except ModuleNotFoundError as e:
    print(f"ERROR: Could not import app. Is apps/api/src/ intact? {e}", file=sys.stderr)
    sys.exit(1)

schema = app.openapi()
# Don't overwrite the app's title — preserve what the app declares
print(json.dumps(schema, indent=2))
`.trim();

console.log('Generating OpenAPI schema from FastAPI app...');
try {
  const scriptPath = path.join(__dirname, '.generate_schema.py');
  fs.writeFileSync(scriptPath, script);

  const result = execFileSync('uv', ['run', 'python', scriptPath], {
    cwd: apiDir,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'pipe'],
    maxBuffer: 10 * 1024 * 1024,
    timeout: 30000,
    shell: false,
  });

  JSON.parse(result); // validate
  fs.writeFileSync(outputPath, result);
  fs.unlinkSync(scriptPath);

  const schema = JSON.parse(result);
  console.log(`Generated ${(fs.statSync(outputPath).size / 1024).toFixed(1)} KB schema with ${Object.keys(schema.paths).length} paths`);
} catch (err) {
  if (err.stderr) console.error(err.stderr);
  if (err.stdout) console.error(err.stdout);
  console.error('Failed to generate OpenAPI schema:', err.message);
  process.exit(1);
}
