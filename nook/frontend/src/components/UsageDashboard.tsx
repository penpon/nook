import {
	Activity,
	AlertCircle,
	Calendar,
	DollarSign,
	RefreshCw,
	TrendingUp,
} from "lucide-react";
import type React from "react";
import { useUsageData } from "../hooks/useUsageData";
import { DailyUsageChart } from "./dashboard/DailyUsageChart";
import { ServiceUsageTable } from "./dashboard/ServiceUsageTable";
import { SummaryCard } from "./dashboard/SummaryCard";

const UsageDashboard: React.FC = () => {
	const {
		summary,
		serviceUsage,
		dailyUsage,
		loading,
		error,
		lastUpdated,
		refetch,
	} = useUsageData();

	const formatNumber = (num: number) => num.toLocaleString();
	const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;

	if (loading && !summary) {
		return (
			<div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
				<div className="max-w-7xl mx-auto">
					<div className="flex items-center justify-center h-64">
						<div className="flex items-center space-x-2">
							<RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
							<span className="text-lg text-gray-600 dark:text-gray-400">
								データを読み込み中...
							</span>
						</div>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
			<div className="max-w-7xl mx-auto">
				{/* ヘッダー */}
				<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
					<div>
						<h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
							LLM API 使用状況ダッシュボード
						</h1>
						<p className="text-gray-600 dark:text-gray-400">
							APIの使用状況とコストを監視します
						</p>
					</div>

					<div className="mt-4 sm:mt-0 flex flex-col sm:flex-row items-start sm:items-center space-y-2 sm:space-y-0 sm:space-x-4">
						{error && (
							<div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400">
								<AlertCircle className="w-4 h-4" />
								<span className="text-sm">モックデータ表示中</span>
							</div>
						)}
						<div className="text-sm text-gray-600 dark:text-gray-400">
							最終更新: {lastUpdated.toLocaleTimeString("ja-JP")}
						</div>
						<button
							onClick={refetch}
							disabled={loading}
							className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-touch touch-manipulation"
						>
							<RefreshCw
								className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
							/>
							<span>更新</span>
						</button>
					</div>
				</div>

				{/* サマリーカード */}
				<div className="dashboard-container cq-xs:grid cq-xs:grid-cols-1 cq-sm:grid-cols-2 cq-lg:grid-cols-4 cq-xs:gap-4 cq-md:gap-6 mb-8">
					<SummaryCard
						title="今日のトークン数"
						value={formatNumber(summary?.todayTokens || 0)}
						icon={<Activity className="w-6 h-6" />}
						colorClass="text-blue-600"
					/>
					<SummaryCard
						title="今日のコスト"
						value={formatCurrency(summary?.todayCost || 0)}
						icon={<DollarSign className="w-6 h-6" />}
						colorClass="text-green-600"
					/>
					<SummaryCard
						title="今月のコスト"
						value={formatCurrency(summary?.monthCost || 0)}
						icon={<Calendar className="w-6 h-6" />}
						colorClass="text-orange-600"
					/>
					<SummaryCard
						title="API呼び出し回数"
						value={formatNumber(summary?.totalCalls || 0)}
						icon={<TrendingUp className="w-6 h-6" />}
						colorClass="text-purple-600"
					/>
				</div>

				{/* サービス別使用量テーブル */}
				<div className="mb-8">
					<ServiceUsageTable serviceUsage={serviceUsage} />
				</div>

				{/* 日次使用量グラフ */}
				<DailyUsageChart dailyUsage={dailyUsage} />
			</div>
		</div>
	);
};

export default UsageDashboard;
