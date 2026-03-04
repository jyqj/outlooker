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
      // NOTE:
      // Vitest 单测文件位于仓库根目录的 ../tests/**，其路径不在 frontend/ 目录树内，
      // 默认的 node_modules 向上查找不会命中 frontend/node_modules，导致 react/jsx-dev-runtime
      // 以及 @testing-library/* 等依赖解析失败。
      // 这里通过 alias 强制这些依赖从 frontend/node_modules 解析，保证 npm test 可运行。
      "react": path.resolve(__dirname, "./node_modules/react"),
      "react-dom": path.resolve(__dirname, "./node_modules/react-dom"),
      "react-router-dom": path.resolve(__dirname, "./node_modules/react-router-dom"),
      "@tanstack/react-query": path.resolve(__dirname, "./node_modules/@tanstack/react-query"),
      "@testing-library/react": path.resolve(__dirname, "./node_modules/@testing-library/react"),
      "@testing-library/user-event": path.resolve(__dirname, "./node_modules/@testing-library/user-event"),
      // JSX transform 可能会注入这些子路径导入
      "react/jsx-runtime": path.resolve(__dirname, "./node_modules/react/jsx-runtime.js"),
      "react/jsx-dev-runtime": path.resolve(__dirname, "./node_modules/react/jsx-dev-runtime.js"),
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
