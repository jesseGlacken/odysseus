import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const schemaPath = resolve(__dirname, '..', 'src', 'generated', 'schema.d.ts');
const clientPath = resolve(__dirname, '..', 'src', 'generated', 'client.ts');

describe('Client SDK generation', () => {
  it('generates schema types file', () => {
    const content = readFileSync(schemaPath, 'utf-8');
    expect(content.length).toBeGreaterThan(10000);
    expect(content).toContain('export interface paths');
    expect(content).toMatchSnapshot();
  });

  it('generates client file', () => {
    const content = readFileSync(clientPath, 'utf-8');
    expect(content).toContain('createClient');
    expect(content).toContain('openapi-fetch');
    expect(content).toContain('/api');
  });

  it('schema has auth paths', () => {
    const schema = readFileSync(schemaPath, 'utf-8');
    // Verify key API paths are typed
    expect(schema).toMatch(/["']\/api\/auth\/login["']/);
    expect(schema).toMatch(/["']\/api\/auth\/status["']/);
    expect(schema).toMatch(/["']\/api\/auth\/logout["']/);
  });
});
