import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: '#1f1a16',
        parchment: '#f7f1e3',
        ember: '#e06d4f',
        gold: '#f2c96d',
        twilight: '#1a2b4f',
      },
      boxShadow: {
        panel: '0 20px 80px rgba(17, 24, 39, 0.18)',
      },
      animation: {
        shimmer: 'shimmer 1.8s linear infinite',
        float: 'float 7s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
