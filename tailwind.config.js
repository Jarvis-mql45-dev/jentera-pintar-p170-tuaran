/**
 * tailwind.config.js — Konfigurasi build Tailwind CSS (FASA 3)
 *
 * Menggantikan Play CDN (cdn.tailwindcss.com) yang HANYA untuk pembangunan:
 *   - CDN memproses kelas dalam pelayar (JIT) → ~400 KB JS + amaran konsol
 *   - Build statik ini menghasilkan satu fail CSS kecil yang di-commit ke repo
 *
 * Build  : npm run css:build
 * Watch  : npm run css:watch
 * Output : frontend/css/tailwind.css  (WAJIB di-commit — Vercel tiada build step Node
 *          untuk aset frontend; lihat vercel.json: @vercel/static + @vercel/python)
 */
module.exports = {
    // Fail yang di-scan untuk nama kelas Tailwind (termasuk HTML yang dijana dalam JS)
    content: [
        './frontend/index.html',
        './frontend/js/**/*.js'
    ],
    theme: {
        extend: {
            colors: {
                // Palet 'primary' ASAL (dipindahkan bulat-bulat dari tailwind.config inline
                // dalam index.html supaya kelas seperti bg-primary-600 kekal sama)
                primary: {
                    50: '#eff6ff',
                    100: '#dbeafe',
                    200: '#bfdbfe',
                    300: '#93c5fd',
                    400: '#60a5fa',
                    500: '#3b82f6',
                    600: '#2563eb',
                    700: '#1d4ed8',
                    800: '#1e40af',
                    900: '#1e3a8a'
                }
            }
        }
    },
    plugins: []
};
