import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [],
  define: {
    'import.meta.env.EXETASI_API_BASE_URL': JSON.stringify(''),
  },
  test: {
    environment: 'jsdom',
    include: ['test/unit/**/*.{spec,test}.ts'],
    exclude: ['test/e2e/**'],
    passWithNoTests: false,
  },
  resolve: {
    alias: {
      src: fileURLToPath(new URL('./src', import.meta.url)),
      components: fileURLToPath(new URL('./src/components', import.meta.url)),
      layouts: fileURLToPath(new URL('./src/layouts', import.meta.url)),
      pages: fileURLToPath(new URL('./src/pages', import.meta.url)),
      boot: fileURLToPath(new URL('./src/boot', import.meta.url)),
    },
  },
});
