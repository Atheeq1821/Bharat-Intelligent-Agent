import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: "#020617",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
