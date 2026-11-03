/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic tokens, driven by CSS variables in index.css (light + dark).
        bg: "rgb(var(--c-bg) / <alpha-value>)",
        card: "rgb(var(--c-card) / <alpha-value>)",
        raised: "rgb(var(--c-raised) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        subtle: "rgb(var(--c-subtle) / <alpha-value>)",
        brand: {
          DEFAULT: "rgb(var(--c-brand) / <alpha-value>)",
          soft: "rgb(var(--c-brand-soft) / <alpha-value>)",
          ink: "rgb(var(--c-brand-ink) / <alpha-value>)",
        },
        iris: {
          DEFAULT: "rgb(var(--c-iris) / <alpha-value>)",
          soft: "rgb(var(--c-iris-soft) / <alpha-value>)",
        },
        ok: {
          DEFAULT: "rgb(var(--c-ok) / <alpha-value>)",
          soft: "rgb(var(--c-ok-soft) / <alpha-value>)",
        },
        warn: {
          DEFAULT: "rgb(var(--c-warn) / <alpha-value>)",
          soft: "rgb(var(--c-warn-soft) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "rgb(var(--c-danger) / <alpha-value>)",
          soft: "rgb(var(--c-danger-soft) / <alpha-value>)",
        },
        bloom: {
          DEFAULT: "rgb(var(--c-bloom) / <alpha-value>)",
          soft: "rgb(var(--c-bloom-soft) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: [
          "Plus Jakarta Sans",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      borderRadius: {
        card: "1.25rem",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgb(15 23 42 / 0.04), 0 12px 32px -18px rgb(15 23 42 / 0.28)",
        lift: "0 2px 6px rgb(15 23 42 / 0.06), 0 22px 48px -24px rgb(15 23 42 / 0.35)",
        glow: "0 10px 30px -12px rgb(79 70 229 / 0.55)",
        inset: "inset 0 1px 0 rgb(255 255 255 / 0.06)",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        pop: {
          "0%": { transform: "scale(0.94)", opacity: "0" },
          "60%": { transform: "scale(1.02)", opacity: "1" },
          "100%": { transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        drawLine: {
          from: { strokeDashoffset: "1000" },
          to: { strokeDashoffset: "0" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
        fadeIn: "fadeIn 0.25s ease-out both",
        pop: "pop 0.32s cubic-bezier(0.22, 1, 0.36, 1) both",
        shimmer: "shimmer 1.6s infinite",
        drawLine: "drawLine 0.9s ease-out both",
      },
    },
  },
  plugins: [],
};
