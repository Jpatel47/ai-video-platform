import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0b0d10",
        panel: "#12161b",
        panelSoft: "#171c22",
        line: "#27303a",
        ink: "#f3f7fb",
        muted: "#9ca9b7",
        teal: "#3dd6c6",
        amber: "#f6c85f",
        rose: "#ff6f91",
        cobalt: "#6ea8fe"
      },
      boxShadow: {
        workspace: "0 22px 70px rgba(0, 0, 0, 0.38)"
      }
    }
  },
  plugins: []
};

export default config;
