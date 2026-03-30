/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-teal': '#0B6C80',
        'brand-gold': '#F7A824',
        'brand-teal-light': '#88C0C3',
        'brand-charcoal': '#3F4644',
        'brand-gray-med': '#797E7C',
        'brand-gray-light': '#E3E3E3',
        'brand-gray-lightest': '#F8F8F8',
        'brand-pink': '#E3A2A2',
        'brand-purple': '#A7B9D3',
      },
      fontFamily: {
        'heading': ['"Brandon Grotesque"', 'sans-serif'],
        'body': ['"Mulish"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
