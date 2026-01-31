import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    preserveSymlinks: false,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      }
    },
    fs: {
      allow: ['..']
    }
  },
  build: {
    outDir: '../data/static',
    emptyOutDir: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./setupTests.ts'],
    include: ['../tests/frontend/unit/**/*.{test,spec}.{ts,tsx}'],
    css: true,
    deps: {
      inline: [
        /^(?!.*\.js$).*\.tsx?$/,
        'react',
        'react-dom',
        'react/jsx-dev-runtime',
        'react/jsx-runtime',
        '@testing-library/react',
        '@testing-library/jest-dom',
        '@testing-library/user-event'
      ]
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        '../tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/main.tsx',
      ],
      thresholds: {
        statements: 60,
        branches: 50,
        functions: 60,
        lines: 60,
      },
    },
  }
})
