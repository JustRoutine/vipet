/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        // VIPET brand colour tokens
        primary:    "#FF007F",  // hot pink — primary CTA / accents
        dark:       "#1A1A1A",  // near-black — headings / body text
        white:      "#FFFFFF",  // pure white — backgrounds / cards
        "light-pink": "#FFE0EF", // blush — subtle backgrounds / hover states
        gray:       "#666666",  // mid-gray — secondary text / borders
      },
      fontFamily: {
        heading: ['"Bodoni Moda"', "Georgia", "serif"],
        body:    ["Jost", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
