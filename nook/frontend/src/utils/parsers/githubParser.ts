import type { ContentItem } from "../../types";

export function parseGitHubTrendingMarkdown(markdown: string): ContentItem[] {
	const lines = markdown.split("\n");
	const contentItems: ContentItem[] = [];
	let currentLanguage = "";

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();

		// 言語セクション（## Python, ## Go, ## Rust）を検出
		if (line.startsWith("## ") && line.length > 3) {
			currentLanguage = line.substring(3).trim();
			contentItems.push({
				title: currentLanguage,
				content: "",
				source: "github",
				isLanguageHeader: true,
			});
		}
		// リポジトリ（### [owner/repo](url)）を検出
		else if (
			line.startsWith("### ") &&
			line.includes("[") &&
			line.includes("](")
		) {
			const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
			if (linkMatch) {
				const repoName = linkMatch[1];
				const repoUrl = linkMatch[2];

				// 次の行から説明とスター数を取得
				let description = "";
				let stars = "";

				// 説明を取得（次の行以降）
				for (let j = i + 1; j < lines.length; j++) {
					const nextLine = lines[j].trim();

					// 次のセクションまたは次のリポジトリに到達したら終了
					if (nextLine.startsWith("#") || nextLine === "---") {
						break;
					}

					if (nextLine.includes("⭐")) {
						// スター数の行
						const starMatch = nextLine.match(/⭐\s*スター数:\s*([0-9,]+)/);
						if (starMatch) {
							stars = starMatch[1];
						}
					} else if (nextLine && !nextLine.startsWith("###")) {
						// 説明の行（空行でない場合のみ）
						if (description && nextLine) {
							description += "\n\n";
						}
						description += nextLine;
					}
				}

				contentItems.push({
					title: repoName,
					content: description + (stars ? `\n\n⭐ ${stars}` : ""),
					url: repoUrl,
					source: "github",
					language: currentLanguage,
					isRepository: true,
				});
			}
		}
	}

	return contentItems;
}
