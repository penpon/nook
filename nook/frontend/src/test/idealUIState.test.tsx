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

	describe("記事番号表示の確認", () => {
		it("記事番号「1」が表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			// まずハッカーニュースヘッダーが表示されるまで待つ
			await waitFor(() => {
				expect(screen.getByText("Hacker News")).toBeInTheDocument();
			}, { timeout: 5000 });

			// 次に記事番号「1」が表示されるまで待つ
			await waitFor(() => {
				// より具体的なセレクターで記事番号を探す
				const articleNumber1 = screen.getByText("1");
				expect(articleNumber1).toBeInTheDocument();
				// 記事番号が正しいスタイルで表示されていることも確認
				expect(articleNumber1.closest('span')).toHaveClass('bg-blue-100');
			}, { timeout: 10000 });
		});

		it("記事番号「2」から「15」が表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				// 記事番号2-15の表示確認
				for (let i = 2; i <= 15; i++) {
					const articleNumber = screen.getByText(i.toString());
					expect(articleNumber).toBeInTheDocument();
				}
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
		it("ダッシュボードメニューが表示されること", async () => {
			render(<App />, { wrapper: TestWrapper });

			await waitFor(() => {
				// 複数のDashboardテキストがある場合は最初のものを取得
				const dashboardTexts = screen.getAllByText("Dashboard");
				expect(dashboardTexts.length).toBeGreaterThan(0);
				expect(dashboardTexts[0]).toBeInTheDocument();
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
				// ヘッダー確認
				expect(
					screen.getByRole("heading", { name: /hacker news/i }),
				).toBeInTheDocument();

				// ナビゲーション確認（複数要素対応）
				const dashboardTexts = screen.getAllByText("Dashboard");
				expect(dashboardTexts.length).toBeGreaterThan(0);
				expect(screen.getByText(/dark mode/i)).toBeInTheDocument();

				// 記事リンクの存在確認
				const articleLinks = screen.getAllByRole("link");
				expect(articleLinks.length).toBeGreaterThan(5);
			}, { timeout: 10000 });

			// 記事番号1の存在確認（理想UI状態の基準）を別途実行
			await waitFor(() => {
				expect(screen.getByText("1")).toBeInTheDocument();
			}, { timeout: 10000 });
		});
	});
});
