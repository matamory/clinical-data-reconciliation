/** @type {import('tailwindcss').Config} */
// Governing: SPEC-0001 REQ "React Frontend with Tailwind CSS", SPEC-0001 REQ "DaisyUI Component Integration"
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["light"],
  },
};
