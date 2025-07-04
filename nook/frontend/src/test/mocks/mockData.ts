// APIモックデータ
export const mockWeatherResponse = {
	temperature: 24.48,
	icon: "01n"
};

// hacker_news.pyの実際のJSONレスポンス形式に基づくモックデータ
export const mockHackerNewsResponse = {
	items: [
		{
			title: "Show HN: AI assistant that can use your dev tools",
			score: 520,
			url: "https://example.com/ai-assistant",
			text: "We built an AI assistant that can interact with development tools directly. It can run tests, check code, and help with debugging. The assistant understands context from your codebase and can suggest improvements based on best practices.",
			summary: "**記事の主な内容**: 開発ツールと直接連携できるAIアシスタントの紹介記事。コードベースのコンテキストを理解し、テスト実行やデバッグ支援を行う。\n\n**重要なポイント**:\n• 開発ツールとの直接連携機能\n• コードベースのコンテキスト理解\n• テスト実行とデバッグ支援\n• ベストプラクティスに基づく改善提案\n• 開発効率の大幅向上\n\n**注目を集めた理由**: 実際の開発ワークフローに組み込める実用的なAIツールとして、開発者コミュニティで高い関心を集めた。"
		},
		{
			title: "Understanding JavaScript Closures",
			score: 342,
			url: "https://example.com/js-closures",
			text: "A comprehensive guide to JavaScript closures, explaining how they work, when to use them, and common pitfalls. Includes practical examples and performance considerations for modern JavaScript development.",
			summary: "**記事の主な内容**: JavaScriptクロージャの包括的なガイド。動作原理、使用場面、よくある落とし穴について詳しく解説。\n\n**重要なポイント**:\n• クロージャの基本概念と動作原理\n• 実践的な使用例とパターン\n• パフォーマンスへの影響と考慮事項\n• よくある間違いと回避方法\n• モダンJavaScript開発での活用法\n\n**注目を集めた理由**: JavaScript開発者にとって重要だが理解が難しいクロージャについて、実用的で分かりやすい解説を提供したため。"
		},
		{
			title: "New React 19 Features You Should Know",
			score: 278,
			url: "https://example.com/react-19",
			text: "React 19 introduces several new features including Server Components, improved hydration, and new hooks. This article covers the most important updates and how they impact development workflows.",
			summary: "**記事の主な内容**: React 19の新機能を紹介する記事。Server Components、改善されたハイドレーション、新しいフックについて解説。\n\n**重要なポイント**:\n• Server Componentsの導入\n• ハイドレーション処理の改善\n• 新しいフックとAPI\n• 開発ワークフローへの影響\n• パフォーマンス向上の恩恵\n\n**注目を集めた理由**: React開発者にとって重要なメジャーアップデートの情報として、コミュニティで広く関心を集めた。"
		},
		{
			title: "Building Scalable Web Applications",
			score: 156,
			url: "https://example.com/scalable-web",
			text: "Best practices for building web applications that can scale to millions of users. Covers architecture patterns, database design, caching strategies, and performance optimization techniques.",
			summary: "**記事の主な内容**: 数百万ユーザーに対応できるスケーラブルなWebアプリケーション構築のベストプラクティス。\n\n**重要なポイント**:\n• アーキテクチャパターンの選択\n• データベース設計の考慮事項\n• キャッシュ戦略の実装\n• パフォーマンス最適化技術\n• 運用監視とメンテナンス\n\n**注目を集めた理由**: 大規模システム開発に関する実践的なノウハウを体系的にまとめた有用な情報として評価された。"
		},
		{
			title: "The Future of TypeScript",
			score: 194,
			url: "https://example.com/typescript-future",
			text: "An analysis of TypeScript's roadmap and upcoming features. Discusses new type system improvements, performance enhancements, and how the language is evolving to meet developer needs.",
			summary: "**記事の主な内容**: TypeScriptのロードマップと今後の機能について分析。型システムの改善、パフォーマンス向上、言語の進化について議論。\n\n**重要なポイント**:\n• 型システムの新機能と改善\n• パフォーマンスの最適化\n• 開発者体験の向上\n• エコシステムとの統合\n• 将来のビジョンと方向性\n\n**注目を集めた理由**: TypeScript開発者にとって重要な将来の方向性について、詳細な分析と予測を提供したため。"
		},
		{
			title: "CSS Grid vs Flexbox: When to Use Which",
			score: 128,
			url: "https://example.com/css-grid-flexbox",
			text: "A practical comparison of CSS Grid and Flexbox, explaining when to use each layout method. Includes real-world examples and best practices for modern web layout design.",
			summary: "**記事の主な内容**: CSS GridとFlexboxの実践的な比較記事。各レイアウト手法の使い分けについて解説。\n\n**重要なポイント**:\n• CSS GridとFlexboxの特徴比較\n• 適切な使い分けの基準\n• 実世界での使用例\n• モダンWebレイアウトのベストプラクティス\n• ブラウザサポートと互換性\n\n**注目を集めた理由**: CSS開発者が迷いがちなレイアウト手法の選択について、明確な指針を提供したため。"
		},
		{
			title: "Database Optimization Techniques",
			score: 203,
			url: "https://example.com/db-optimization",
			text: "Advanced database optimization techniques covering indexing strategies, query optimization, and performance tuning. Includes examples for PostgreSQL, MySQL, and MongoDB.",
			summary: "**記事の主な内容**: データベース最適化の高度な技術について解説。インデックス戦略、クエリ最適化、パフォーマンスチューニングを扱う。\n\n**重要なポイント**:\n• インデックス設計の戦略\n• クエリ最適化の手法\n• パフォーマンスチューニング\n• 複数DBでの実装例\n• 監視とメンテナンス\n\n**注目を集めた理由**: データベースパフォーマンスに関する実践的で詳細な技術情報として、開発者から高く評価された。"
		},
		{
			title: "Modern JavaScript Testing Strategies",
			score: 167,
			url: "https://example.com/js-testing",
			text: "Comprehensive guide to modern JavaScript testing approaches. Covers unit testing, integration testing, end-to-end testing, and test-driven development best practices.",
			summary: "**記事の主な内容**: モダンJavaScriptテスト戦略の包括的ガイド。ユニットテスト、統合テスト、E2Eテストについて解説。\n\n**重要なポイント**:\n• 各種テスト手法の使い分け\n• テスト駆動開発のベストプラクティス\n• モダンテストツールの活用\n• CI/CDとの統合\n• テスト品質の向上\n\n**注目を集めた理由**: JavaScript開発における品質保証について、体系的で実践的な情報を提供したため。"
		},
		{
			title: "API Design Best Practices",
			score: 142,
			url: "https://example.com/api-design",
			text: "Essential principles for designing robust and user-friendly APIs. Covers REST design patterns, versioning strategies, authentication, and documentation best practices.",
			summary: "**記事の主な内容**: 堅牢でユーザーフレンドリーなAPI設計の基本原則。REST設計パターン、バージョニング戦略について解説。\n\n**重要なポイント**:\n• REST API設計の原則\n• バージョニング戦略\n• 認証とセキュリティ\n• ドキュメント作成のベストプラクティス\n• エラーハンドリング\n\n**注目を集めた理由**: API設計に関する包括的で実用的なガイドとして、開発者コミュニティで広く参照された。"
		},
		{
			title: "Microservices vs Monoliths",
			score: 198,
			url: "https://example.com/microservices-monoliths",
			text: "Detailed comparison of microservices and monolithic architectures. Discusses trade-offs, migration strategies, and when to choose each approach for different project requirements.",
			summary: "**記事の主な内容**: マイクロサービスとモノリシックアーキテクチャの詳細な比較。トレードオフ、移行戦略について議論。\n\n**重要なポイント**:\n• 各アーキテクチャの特徴と比較\n• プロジェクト要件に応じた選択基準\n• 移行戦略とリスク管理\n• 運用コストと複雑性\n• チーム構成への影響\n\n**注目を集めた理由**: アーキテクチャ選択の重要な判断材料として、バランスの取れた分析を提供したため。"
		},
		{
			title: "Docker Container Security",
			score: 176,
			url: "https://example.com/docker-security",
			text: "Comprehensive guide to securing Docker containers in production. Covers image security, runtime protection, network security, and compliance best practices.",
			summary: "**記事の主な内容**: 本番環境でのDockerコンテナセキュリティの包括的ガイド。イメージセキュリティ、ランタイム保護について解説。\n\n**重要なポイント**:\n• コンテナイメージのセキュリティ\n• ランタイム保護の実装\n• ネットワークセキュリティ\n• コンプライアンス要件\n• 脆弱性管理とスキャン\n\n**注目を集めた理由**: コンテナ技術の普及に伴い重要性が増すセキュリティについて、実践的なガイドを提供したため。"
		},
		{
			title: "Machine Learning for Developers",
			score: 234,
			url: "https://example.com/ml-developers",
			text: "Practical introduction to machine learning for software developers. Covers fundamental concepts, popular frameworks, and real-world implementation strategies.",
			summary: "**記事の主な内容**: ソフトウェア開発者向けの機械学習実践入門。基本概念、人気フレームワーク、実装戦略について解説。\n\n**重要なポイント**:\n• 機械学習の基本概念\n• 開発者向けフレームワーク\n• 実世界での実装戦略\n• データ処理とモデル構築\n• 本番環境での運用\n\n**注目を集めた理由**: AI/ML技術への関心が高まる中、開発者向けの実践的な入門ガイドとして高く評価された。"
		},
		{
			title: "Cloud Native Development",
			score: 159,
			url: "https://example.com/cloud-native",
			text: "Guide to cloud-native development practices. Covers containerization, orchestration, service mesh, and observability patterns for modern cloud applications.",
			summary: "**記事の主な内容**: クラウドネイティブ開発実践のガイド。コンテナ化、オーケストレーション、サービスメッシュについて解説。\n\n**重要なポイント**:\n• クラウドネイティブの原則\n• コンテナオーケストレーション\n• サービスメッシュアーキテクチャ\n• 可観測性パターン\n• DevOpsとの統合\n\n**注目を集めた理由**: クラウド移行が進む中、クラウドネイティブ開発の実践的な知識として注目された。"
		},
		{
			title: "GraphQL vs REST API",
			score: 187,
			url: "https://example.com/graphql-rest",
			text: "Comprehensive comparison of GraphQL and REST APIs. Analyzes performance, flexibility, complexity, and use cases to help choose the right approach.",
			summary: "**記事の主な内容**: GraphQLとREST APIの包括的比較。パフォーマンス、柔軟性、複雑性を分析し、適切な選択指針を提供。\n\n**重要なポイント**:\n• 各APIアプローチの特徴\n• パフォーマンス比較と考慮事項\n• 実装の複雑性とメンテナンス\n• 適用場面の使い分け\n• ツールとエコシステム\n\n**注目を集めた理由**: API設計における重要な選択について、客観的で詳細な比較分析を提供したため。"
		},
		{
			title: "Web Performance Optimization",
			score: 145,
			url: "https://example.com/web-performance",
			text: "Advanced techniques for optimizing web application performance. Covers loading strategies, caching, code splitting, and modern performance metrics.",
			summary: "**記事の主な内容**: Webアプリケーションパフォーマンス最適化の高度な技術。ローディング戦略、キャッシング、コード分割について解説。\n\n**重要なポイント**:\n• ロード戦略の最適化\n• 効果的なキャッシング手法\n• コード分割とバンドル最適化\n• モダンパフォーマンス指標\n• ユーザー体験の改善\n\n**注目を集めた理由**: Webパフォーマンスの重要性が高まる中、実践的で効果的な最適化技術を紹介したため。"
		}
	]
};