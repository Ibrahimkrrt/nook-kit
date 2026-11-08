// Shared Vite setup for every Nook front end.
//   import { nookVite } from '@nook/kit/vite';
//   export default nookVite({ id: 'chomp' });          // an app, served at /chomp/
//   export default nookVite({ id: null });             // the Nook home itself, served at /
//
// What it does:
//   * base path = /<id>/ (the hub serves each app's dist under its own id)
//   * dev server proxies /api to the running hub, so the real back end answers
//   * @nook/kit is compiled as source (it ships JSX), and React/Motion are de-duplicated
//   * NOOK_KIT_DEV=1 npm run dev  → uses the kit checkout next door (../../kit/src) live,
//     for working on the kit and an app at the same time
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import react from '@vitejs/plugin-react';

const KIT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function nookVite({ id, hub = 'http://127.0.0.1:8765', port, extend = {} } = {}) {
  const devKit = process.env.NOOK_KIT_DEV
    ? path.resolve(process.cwd(), process.env.NOOK_KIT_DEV === '1' ? '../../kit' : process.env.NOOK_KIT_DEV)
    : null;
  return {
    base: id ? `/${id}/` : '/',
    plugins: [react()],
    resolve: {
      dedupe: ['react', 'react-dom', 'motion', 'lucide-react'],
      alias: devKit
        ? [
            { find: /^@nook\/kit\/styles\.css$/, replacement: path.join(devKit, 'src/styles/index.css') },
            { find: /^@nook\/kit\/icons$/, replacement: path.join(devKit, 'src/icons.js') },
            { find: /^@nook\/kit$/, replacement: path.join(devKit, 'src/index.js') },
          ]
        : [],
    },
    optimizeDeps: {
      exclude: ['@nook/kit'],
      include: ['react', 'react-dom', 'react-dom/client', 'motion/react', 'lucide-react'],
    },
    server: {
      port,
      proxy: { '/api': { target: hub, changeOrigin: true } },
      fs: { allow: [process.cwd(), KIT_ROOT, ...(devKit ? [devKit] : [])] },
    },
    build: { target: 'es2022', sourcemap: false, chunkSizeWarningLimit: 700 },
    ...extend,
  };
}
