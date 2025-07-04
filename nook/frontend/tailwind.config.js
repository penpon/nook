/** @type {import('tailwindcss').Config} */
export default {
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	darkMode: "class",
	theme: {
		extend: {
			minHeight: {
				touch: "44px",
				"touch-large": "48px",
			},
			minWidth: {
				touch: "44px",
				"touch-large": "48px",
			},
			spacing: {
				touch: "44px",
				"touch-large": "48px",
			},
			colors: {
				blue: {
					50: "#eff6ff",
					100: "#dbeafe",
					200: "#bfdbfe",
					300: "#93c5fd",
					400: "#60a5fa",
					500: "#3b82f6",
					600: "#2563eb",
					700: "#1d4ed8",
					800: "#1e40af",
					900: "#1e3a8a",
				},
			},
			typography: {
				DEFAULT: {
					css: {
						maxWidth: "100%",
						width: "100%",
						fontSize: "1.25rem",
						p: {
							fontSize: "1.25rem",
						},
						li: {
							fontSize: "1.25rem",
						},
						h1: {
							fontSize: "2.25rem",
						},
						h2: {
							fontSize: "1.875rem",
						},
						h3: {
							fontSize: "1.5rem",
						},
					},
				},
			},
		},
	},
	plugins: [
		require("@tailwindcss/typography"),
		// @tailwindcss/container-queries を削除
	],
};
