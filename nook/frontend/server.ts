import middie from "@fastify/middie";
import Fastify from "fastify";
import fastifyStatic from "fastify-static";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isProduction = process.env.NODE_ENV === "production";

async function createServer() {
	const app = Fastify({
		logger: true,
		requestTimeout: 30000,
	});

	await app.register(middie);

	let vite;

	if (!isProduction) {
		// 開発モード
		vite = await createViteServer({
			server: { middlewareMode: true },
			appType: "custom",
		});

		app.use(vite.middlewares);
	} else {
		// 本番モード
		app.register(fastifyStatic, {
			root: path.join(__dirname, "dist/client"),
			prefix: "/",
		});
	}

	app.get("*", async (request, reply) => {
		const url = request.url;

		try {
			let template, render;

			if (!isProduction) {
				// 開発モードでテンプレートを読み込み
				template = await vite.transformIndexHtml(
					url,
					`<!DOCTYPE html>
          <html lang="ja">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>Nook</title>
              <!--app-head-->
            </head>
            <body>
              <div id="root"><!--app-html--></div>
              <script type="module" src="/src/entry-client.tsx"></script>
            </body>
          </html>`,
				);

				render = (await vite.ssrLoadModule("/src/entry-server.tsx")).render;
			} else {
				// 本番モード
				template = await fs.readFile(
					path.join(__dirname, "dist/client/index.html"),
					"utf-8",
				);

				render = (await import("./dist/server/entry-server.js")).render;
			}

			// SSRレンダリング
			const { html: appHtml, head } = await render(url, {
				request,
				reply,
			});

			// HTMLテンプレートに挿入
			const html = template
				.replace("<!--app-head-->", head)
				.replace("<!--app-html-->", appHtml);

			reply.type("text/html").send(html);
		} catch (e) {
			if (!isProduction && vite) {
				vite.ssrFixStacktrace(e);
			}
			console.error(e);
			reply.code(500).send(e.message);
		}
	});

	const port = process.env.PORT || 3000;
	await app.listen({ port: +port, host: "0.0.0.0" });

	console.log(`Server running at http://localhost:${port}`);
}

createServer();
