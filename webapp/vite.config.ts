import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // import.meta.dirname, not __dirname: Vite 8 warns that __dirname is
      // unsupported by configLoader: 'native', which becomes the default in a
      // future major. Changing it now keeps the config loading after that.
      '@': path.resolve(import.meta.dirname, './src')
    }
  },
  optimizeDeps: {
    exclude: ['lucide-react']
  }
});