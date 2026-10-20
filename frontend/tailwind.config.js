/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: { 950: '#0b1020', 900: '#111827', 800: '#1a2233', 700: '#273246', 600: '#3a4660' },
        accent: { cpu: '#38bdf8', memory: '#a78bfa', disk: '#fbbf24', rx: '#34d399', tx: '#fb7185' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
    },
  },
  plugins: [],
};
