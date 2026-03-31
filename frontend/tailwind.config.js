/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#00fff0",
        dark: "#0f0c29",
        card: "#1a1a2e",
        accent: "#302b63",
      },
      animation: {
        pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        spin: "spin 3s linear infinite",
        bounce: "bounce 1s infinite",
      },
    },
  },
  plugins: [],
};
