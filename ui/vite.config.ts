import { federation } from '@module-federation/vite';
import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig(() => {
	return {
		server: {
			fs: {
				allow: ['.', '../shared'],
			},
		},
		build: {
			target: 'chrome89',
		},
		plugins: [
			federation({
				filename: 'remoteEntry.js',
				name: 'tak-integration',
				exposes: {
					'./remote-ui': './src/App.tsx',
				},
				remotes: {},
				shared: {
					react: {
						requiredVersion: "19.1.1",
						singleton: true,
					},
				},
				runtime: '@module-federation/enhanced/runtime',
			}),
			react(),
			tailwindcss()
		],
		resolve: {
			alias: {
				"@": path.resolve(__dirname, "./src"),
			},
		},
		define: {
			__USE_GLOBAL_CSS__: JSON.stringify(process.env.VITE_USE_GLOBAL_CSS === "true"),
		},
	};
});
