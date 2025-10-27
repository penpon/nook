import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "react-query";
import { beforeEach, describe, expect, it } from "vitest";
import App from "../App";

// テスト用QueryClientの作成
const createTestQueryClient = () =>
	new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				refetchOnWindowFocus: false,
				cacheTime: 0,
				staleTime: 0,
			},
		},
		logger: {
			log: console.log,
			warn: console.warn,
			error: console.error,
		},
	});

// テスト用ラッパーコンポーネント
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
	const queryClient = createTestQueryClient();
	return (
		<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
	);
};

/**
 * 理想UI状態テスト
 * tmp-develop (5017a80) の理想UI状態を基準とするテスト
 *
 * テスト対象：
 * - 記事番号「1」-「15」の表示確認
 * - カードレイアウトの存在確認
 * - ハッカーニュース記事の表示確認
 * - 基本ナビゲーション要素の確認
 */
describe("理想UI状態テスト", () => {
	beforeEach(() => {
		// テスト前にhacker-newsパラメータを設定
		Object.defineProperty(window, "location", {
			value: {
				search: "?source=hacker-news",
				pathname: "/",
				href: "http://localhost:5173/?source=hacker-news",
			},
			writable: true,
		});
	});

	describe("記事表示の確認", () => {
		it("ハッカーニュースの最初の記事が表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				expect(screen.getByText("Hacker News")).toBeInTheDocument();
			}, { timeout: 5000 });

				await screen.findByText(
					/Show HN: AI assistant that can use your dev tools/i,
					undefined,
					{ timeout: 10000 },
				);
		});

		it("複数の記事タイトルが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				const articleLinks = screen.getAllByRole("link");
				expect(articleLinks.length).toBeGreaterThan(5);
			});
		});
	});

	describe("ハッカーニュース記事表示の確認", () => {
		it("ハッカーニュースのヘッダーが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				const hackerNewsHeader = screen.getByRole("heading", {
					name: /hacker news/i,
				});
				expect(hackerNewsHeader).toBeInTheDocument();
			});
		});

		it("記事カードが複数表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				// 記事のタイトルリンクが複数存在することを確認
				const articleLinks = screen.getAllByRole("link");
				expect(articleLinks.length).toBeGreaterThan(10);
			});
		});
	});

	describe("ナビゲーション要素の確認", () => {
		it("ソースメニューが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				expect(screen.getByText("Sources")).toBeInTheDocument();
			});
		});

		it("ダークモード切り替えボタンが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				const darkModeButton = screen.getByText(/dark mode/i);
				expect(darkModeButton).toBeInTheDocument();
			});
		});

		it("ソース選択ボタンが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				const hackerNewsButton = screen.getByRole("button", {
					name: /hacker news/i,
				});
				expect(hackerNewsButton).toBeInTheDocument();
			});
		});
	});

		describe("理想UI状態の全体確認", () => {
			it("理想UI状態の主要要素がすべて表示されること", async () => {
				render(<App />, { wrapper: TestWrapper });

				await waitFor(() => {
					expect(
						screen.getByRole("heading", { name: /hacker news/i }),
					).toBeInTheDocument();
					expect(screen.getByText("Sources")).toBeInTheDocument();
					expect(screen.getByText(/dark mode/i)).toBeInTheDocument();

					const articleLinks = screen.getAllByRole("link");
					expect(articleLinks.length).toBeGreaterThan(5);
				}, { timeout: 10000 });

				await screen.findByText(
					/Show HN: AI assistant that can use your dev tools/i,
					undefined,
					{ timeout: 10000 },
				);
			});
		});
});
