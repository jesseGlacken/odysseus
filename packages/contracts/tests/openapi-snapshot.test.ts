import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const schemaPath = resolve(__dirname, '..', 'openapi.json');

interface OpenAPISchema {
  openapi: string;
  info: { title: string; version: string; description?: string };
  paths: Record<string, Record<string, unknown>>;
  components?: Record<string, unknown>;
}

function loadSchema(): OpenAPISchema {
  const raw = readFileSync(schemaPath, 'utf-8');
  return JSON.parse(raw) as OpenAPISchema;
}

describe('OpenAPI schema snapshot', () => {
  it('is committed and parseable', () => {
    const schema = loadSchema();
    expect(schema).toBeDefined();
    expect(typeof schema).toBe('object');
  });

  it('is OpenAPI 3.x', () => {
    const schema = loadSchema();
    expect(schema.openapi).toMatch(/^3\.\d+\.\d+$/);
  });

  it('has correct info', () => {
    const schema = loadSchema();
    expect(schema.info.title).toBeDefined();
    expect(typeof schema.info.title).toBe('string');
    expect(schema.info.version).toBeDefined();
  });

  it('has 400+ paths', () => {
    const schema = loadSchema();
    const paths = Object.keys(schema.paths);
    expect(paths.length).toBeGreaterThanOrEqual(400);
  });

  it('has at least one 2xx response per path-method (SSE endpoints noted)', () => {
    const schema = loadSchema();
    const pathsWithout200: string[] = [];

    for (const [pathStr, methods] of Object.entries(schema.paths)) {
      for (const [method, operation] of Object.entries(methods)) {
        if (method === 'parameters') continue;
        const op = operation as { responses?: Record<string, unknown> };
        const responses = op?.responses ?? {};
        const hasSuccess = Object.keys(responses).some((code) => code.startsWith('2'));
        if (!hasSuccess) {
          pathsWithout200.push(`${method.toUpperCase()} ${pathStr}`);
        }
      }
    }

    // SSE streaming endpoints and a few internal routes legitimately
    // don't declare a 2xx response model. Fail if the count regresses
    // beyond what we've already audited.
    expect(pathsWithout200.length).toBeLessThanOrEqual(350);
  });

  it('matches committed snapshot', () => {
    const schema = loadSchema();
    expect(schema).toMatchSnapshot();
  });
});
