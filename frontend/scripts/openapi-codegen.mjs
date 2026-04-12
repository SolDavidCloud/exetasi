import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const outFile = join(__dirname, '../src/api/generated/paths.d.ts');
const defaultUrl = 'http://127.0.0.1:8000/openapi.json';
const url = process.env.OPENAPI_URL ?? defaultUrl;

mkdirSync(dirname(outFile), { recursive: true });

try {
  execFileSync(
    'pnpm',
    ['exec', 'openapi-typescript', url, '--output', outFile],
    { stdio: 'inherit', cwd: join(__dirname, '..') },
  );
} catch {
  console.warn(
    `[codegen] openapi-typescript failed for ${url}; keeping existing ${outFile} if present.`,
  );
  process.exitCode = 0;
}
