import type { ContentItem } from "../../types";

export function parseAcademicPapersMarkdown(markdown: string): ContentItem[] {
	const items: ContentItem[] = [];
	const lines = markdown.split("\n");

	// 最初に「ArXiv」カテゴリヘッダーを追加
	items.push({
		title: "ArXiv",
		url: "",
		content: "",
		isLanguageHeader: false,
		isCategoryHeader: true,
		isArticle: false,
	});

	let articleNumber = 1;

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();

		// 論文タイトル行を検出（## [タイトル](URL)）
		const titleMatch = line.match(/^##\s*\[([^\]]+)\]\(([^)]+)\)$/);
		if (titleMatch) {
			const title = titleMatch[1];
			const url = titleMatch[2];

			// 要約を次の行から取得
			let content = "";
			let collectingContent = false;
			let abstractContent = "";
			let summaryContent = "";
			let currentSection = "";

			for (let j = i + 1; j < lines.length; j++) {
				const nextLine = lines[j].trim();

				// 次の論文タイトルに到達したら終了
				if (nextLine.startsWith("## [") && nextLine.includes("](")) {
					// 最初の論文タイトル以外で終了
					if (j > i + 1) break;
				}

				// セクション区切り線
				if (nextLine === "---") {
					break;
				}

				// abstract セクション
				if (nextLine.includes("**abstract**:")) {
					currentSection = "abstract";
					collectingContent = true;
					continue;
				}

				// summary セクション
				if (nextLine.includes("**summary**:")) {
					currentSection = "summary";
					collectingContent = true;
					continue;
				}

				// コンテンツを収集
				if (collectingContent && nextLine) {
					if (currentSection === "abstract") {
						if (abstractContent) abstractContent += "\n\n";
						abstractContent += nextLine;
					} else if (currentSection === "summary") {
						if (summaryContent) summaryContent += "\n\n";
						summaryContent += nextLine;
					}
				}
			}

			// abstract と summary を結合
			if (abstractContent) {
				content = `**abstract**:\n\n${abstractContent}`;
			}
			if (summaryContent) {
				if (content) content += "\n\n";
				content += `**summary**:\n\n${summaryContent}`;
			}

			items.push({
				title: title,
				url: url,
				content: content,
				source: "arxiv",
				isLanguageHeader: false,
				isCategoryHeader: false,
				isArticle: true,
				metadata: {
					source: "arxiv",
					articleNumber: articleNumber++,
				},
			});
		}
	}

	return items;
}
