/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Fluent Design inspired colors
        fluent: {
          blue: {
            50: '#e6f2ff',
            100: '#b3d9ff',
            200: '#80bfff',
            300: '#4da6ff',
            400: '#1a8cff',
            500: '#0078d4', // Primary blue
            600: '#106ebe',
            700: '#005a9e',
            800: '#004578',
            900: '#003152',
          },
          gray: {
            50: '#fafafa',
            100: '#f3f2f1',
            200: '#edebe9',
            300: '#e1dfdd',
            400: '#d2d0ce',
            500: '#c8c6c4',
            600: '#a19f9d',
            700: '#605e5c',
            800: '#323130',
            900: '#201f1e',
          },
          success: '#00c853',
          warning: '#ffb900',
          error: '#d13438',
          info: '#38bdf8',
        },
        // Executive dark palette
        midnight: {
          800: '#0f172a',
          700: '#111827',
          600: '#14213d',
          500: '#1b2439',
        },
        dark: {
          bg: {
            primary: '#0f172a',
            secondary: '#111827',
            tertiary: '#1b2435',
            elevated: '#1f2a3d',
          },
          border: '#2a3650',
          text: {
            primary: '#f8fafc',
            secondary: '#cbd5f5',
            tertiary: '#94a3d5',
          }
        }
      },
      boxShadow: {
        'fluent': '0 3.2px 7.2px 0 rgba(0,0,0,.13), 0 0.6px 1.8px 0 rgba(0,0,0,.11)',
        'fluent-lg': '0 6.4px 14.4px 0 rgba(0,0,0,.13), 0 1.2px 3.6px 0 rgba(0,0,0,.11)',
        'fluent-xl': '0 25.6px 57.6px 0 rgba(0,0,0,.22), 0 4.8px 14.4px 0 rgba(0,0,0,.18)',
        'acrylic': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
      backdropBlur: {
        'acrylic': '40px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
    },
  },
  plugins: [],
}
