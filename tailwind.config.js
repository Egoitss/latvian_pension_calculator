// Tailwind build config — replaces the former CDN runtime config that
// lived inline in templates/base.html. Rebuild static/css/tailwind.css
// after template/JS class changes:
//   npx tailwindcss@3.4.17 -i src/tailwind.css \
//     -o static/css/tailwind.css --minify
module.exports = {
  content: [
    // Top-level JS only: static/js/vendor/ holds minified libraries
    // whose string tokens must not leak into the class scan.
    "./templates/**/*.html",
    "./static/js/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
      },
    },
  },
};
