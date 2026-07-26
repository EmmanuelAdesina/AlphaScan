import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Enterprise palette — mature, professional
        bg: {
          DEFAULT: '#09090B',
          card: '#111113',
          elevated: '#18181B',
          hover: '#1E1E21',
        },
        border: {
          DEFAULT: '#232326',
          hover: '#3F3F44',
        },
        primary: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
          muted: '#3B82F6/20',
        },
        success: {
          DEFAULT: '#10B981',
          hover: '#059669',
          muted: '#10B981/20',
        },
        danger: {
          DEFAULT: '#EF4444',
          hover: '#DC2626',
          muted: '#EF4444/20',
        },
        warning: {
          DEFAULT: '#F59E0B',
          hover: '#D97706',
          muted: '#F59E0B/20',
        },
        info: {
          DEFAULT: '#06B6D4',
          hover: '#0891B2',
          muted: '#06B6D4/20',
        },
        critical: {
          DEFAULT: '#DC2626',
          glow: '#DC2626/15',
        },
        text: {
          primary: '#FAFAFA',
          secondary: '#A1A1AA',
          muted: '#71717A',
          inverted: '#09090B',
        },
        // Provider brand colors
        provider: {
          github: '#6E40C9',
          aws: '#FF9900',
          openai: '#412991',
          anthropic: '#D97706',
          stripe: '#635BFF',
          google: '#4285F4',
          gitlab: '#FC6D26',
          discord: '#5865F2',
          slack: '#4A154B',
          cloudflare: '#F38020',
          sendgrid: '#1B3F8B',
          twilio: '#F22F46',
          mongodb: '#47A248',
          postgresql: '#336791',
          redis: '#DC382D',
          ethereum: '#8C8C8C',
          bitcoin: '#F7931A',
          solana: '#9945FF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0,0,0,0.3), 0 1px 2px -1px rgba(0,0,0,0.3)',
        'card-hover': '0 4px 6px -1px rgba(0,0,0,0.4), 0 2px 4px -2px rgba(0,0,0,0.3)',
        'glow-critical': '0 0 15px 0 rgba(220,38,38,0.15)',
        'glow-danger': '0 0 10px 0 rgba(239,68,68,0.12)',
        'glow-success': '0 0 10px 0 rgba(16,185,129,0.12)',
        'glow-primary': '0 0 10px 0 rgba(59,130,246,0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-right': 'slideRight 0.2s ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
        'count-up': 'countUp 0.6s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideRight: {
          '0%': { opacity: '0', transform: 'translateX(-8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.85' },
        },
        countUp: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};

export default config;
