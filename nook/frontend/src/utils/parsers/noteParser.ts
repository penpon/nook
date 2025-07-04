import type { ContentItem } from "../../types";

export function parseNoteArticlesMarkdown(markdown: string): ContentItem[] {
	const lines = markdown.split("\n");
	const contentItems: ContentItem[] = [];

	// 最初に「note」カテゴリヘッダーを追加
	contentItems.push({
		title: "note",
		content: "",
		source: "note",
		isCategoryHeader: true,
	});

	let articleNumber = 1;

	// 記事の解析
	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();

		// 日付付きタイトル（# note記事 (2025-06-24)）を無視
		if (line.startsWith("# note記事")) {
			continue;
		}

		// 記事タイトル行を検出（### [タイトル](URL)）
		if (line.startsWith("### ") && line.includes("[") && line.includes("](")) {
			const titleMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
			if (titleMatch) {
				const title = titleMatch[1];
				const url = titleMatch[2];

				// 要約を抽出
				let summary = "";

				// 要約を取得（次の行以降）
				for (let j = i + 1; j < lines.length; j++) {
					const nextLine = lines[j].trim();

					// 次のセクションまたは次の記事に到達したら終了
					if (nextLine.startsWith("#") || nextLine === "---") {
						break;
					}

					if (nextLine.startsWith("**要約**:")) {
						// 要約情報の開始
						summary = nextLine.replace("**要約**:", "").trim();

						// 要約の続きがある場合は次の行も読み込み
						for (let k = j + 1; k < lines.length; k++) {
							const summaryLine = lines[k].trim();

							// 次のセクション、記事、または区切り線に到達したら終了
							if (
								summaryLine.startsWith("#") ||
								summaryLine === "---" ||
								summaryLine.startsWith("**")
							) {
								break;
							}

							if (summaryLine) {
								summary += "\n\n" + summaryLine;
							}
						}
					}
				}

				// コンテンツの構築
				let content = "";
				if (summary) {
					content = `**要約**:\n${summary}`;
				}

				contentItems.push({
					title: title,
					content: content,
					url: url,
					source: "note",
					isArticle: true,
					metadata: {
						source: "note",
						articleNumber: articleNumber++,
					},
				});
			}
		}
	}

	return contentItems;
}
