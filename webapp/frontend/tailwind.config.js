/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        page: '#FFFDF8',
        surface: '#FFFFFF',
        'surface-muted': '#F2F0F5',
        sidebar: '#111116',
        'sidebar-panel': '#24242D',
        'text-primary': '#17171D',
        'text-secondary': '#62616D',
        'text-inverse': '#FFFFFF',
        border: '#E2E0E8',
        'border-strong': '#C9C6D2',
        steel: '#777782',
        mist: '#E7E6EC',
        graphite: '#24242D',

        // Brand Accents
        'royal-blue': '#155EEF',
        'electric-blue': '#087CFF',
        'laser-blue': '#00B7FF',
        'royal-purple': '#6528E0',
        'neon-violet': '#873CFF',
        'electric-purple': '#A020F0',
        'fuchsia-brand': '#E6007E',
        'hot-pink': '#FF28A8',
        'neon-magenta': '#FF00A8',

        // Semantic
        success: '#16A36A',
        warning: '#E99A18',
        error: '#E5485D',
        info: '#087CFF',
        pending: '#8B6CE8',
        disabled: '#A6A6AF',
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(90deg, #155EEF 0%, #6528E0 50%, #E6007E 100%)',
        'gradient-ai': 'linear-gradient(90deg, #00B7FF 0%, #873CFF 50%, #FF28A8 100%)',
        'gradient-purple-pink': 'linear-gradient(90deg, #6528E0 0%, #A020F0 50%, #FF28A8 100%)',
        'gradient-dark': 'linear-gradient(180deg, #111116 0%, #1A1A22 100%)',
        'gradient-glow': 'radial-gradient(circle at 50% 0%, rgba(135, 60, 255, 0.25) 0%, transparent 70%)',
      },
      boxShadow: {
        'glow-blue': '0 0 10px rgba(21, 94, 239, 0.65), 0 0 28px rgba(8, 124, 255, 0.45)',
        'glow-purple': '0 0 12px rgba(135, 60, 255, 0.65), 0 0 32px rgba(101, 40, 224, 0.45)',
        'glow-pink': '0 0 12px rgba(255, 40, 168, 0.65), 0 0 30px rgba(230, 0, 126, 0.40)',
        'glow-brand': '0 0 14px rgba(135, 60, 255, 0.55), 0 0 34px rgba(230, 0, 126, 0.30)',
        'card': '0 4px 20px -2px rgba(17, 17, 22, 0.05), 0 2px 6px -1px rgba(17, 17, 22, 0.03)',
        'card-hover': '0 12px 32px -4px rgba(101, 40, 224, 0.12), 0 4px 12px -2px rgba(17, 17, 22, 0.05)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'card': '16px',
        'btn': '11px',
      }
    },
  },
  plugins: [],
}

