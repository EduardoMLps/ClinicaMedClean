/** Paleta oficial do sistema — telas em tons de verde, textos em azul-marinho escuro. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#F0FDF6",
          100: "#DCFCE9",
          200: "#B8F5D0",
          300: "#84E8AE",
          400: "#4CD388",
          500: "#22B36B", // verde principal
          600: "#159157",
          700: "#0F7347",
          800: "#0C5B3A",
          900: "#0A4A30",
        },
        ink: {
          50: "#EEF2F8",
          100: "#D7E0EC",
          300: "#7C8CA8",
          500: "#38507A",
          700: "#1B2E52",
          800: "#122040",
          900: "#0B1730", // azul-marinho principal (texto)
        },
      },
      fontFamily: {
        sans: ["Poppins", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 20px -4px rgba(11, 23, 48, 0.12)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
