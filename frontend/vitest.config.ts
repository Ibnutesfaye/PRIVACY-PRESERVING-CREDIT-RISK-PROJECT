import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    // The Windows development environment can time out while spawning forked
    // workers. A single worker is deterministic for this small UI suite.
    pool: 'threads',
    maxWorkers: 1,
    fileParallelism: false,
  },
})
