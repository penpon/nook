import type React from "react";
import {
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { useTheme } from "../../hooks/useTheme";
import type { DailyUsage } from "../../hooks/useUsageData";

interface DailyUsageChartProps {
	dailyUsage: DailyUsage[];
}

export const DailyUsageChart: React.FC<DailyUsageChartProps> = ({
	dailyUsage,
}) => {
	const { darkMode } = useTheme();
	const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;

	return (
		<div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
			<div className="p-6 border-b border-gray-200 dark:border-gray-700">
				<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
					日別コスト推移（過去30日）
				</h3>
			</div>

			<div className="p-6">
				<div className="w-full h-80 sm:h-96">
					<ResponsiveContainer width="100%" height="100%">
						<BarChart
							data={dailyUsage}
							margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
						>
							<CartesianGrid
								strokeDasharray="3 3"
								stroke={darkMode ? "#374151" : "#e5e7eb"}
							/>
							<XAxis
								dataKey="date"
								tick={{
									fontSize: 12,
									fill: darkMode ? "#9ca3af" : "#6b7280",
								}}
								stroke={darkMode ? "#6b7280" : "#9ca3af"}
								interval="preserveStartEnd"
							/>
							<YAxis
								tick={{
									fontSize: 12,
									fill: darkMode ? "#9ca3af" : "#6b7280",
								}}
								stroke={darkMode ? "#6b7280" : "#9ca3af"}
							/>
							<Tooltip
								formatter={(value: number) => [formatCurrency(value), "コスト"]}
								labelFormatter={(label) => `日付: ${label}`}
								contentStyle={{
									backgroundColor: darkMode ? "#374151" : "#ffffff",
									border: `1px solid ${darkMode ? "#4b5563" : "#e5e7eb"}`,
									borderRadius: "8px",
									color: darkMode ? "#f3f4f6" : "#1f2937",
								}}
							/>
							<Legend
								wrapperStyle={{
									color: darkMode ? "#f3f4f6" : "#1f2937",
								}}
							/>
							<Bar
								dataKey="totalCost"
								fill="#3b82f6"
								name="総コスト"
								radius={[4, 4, 0, 0]}
							/>
						</BarChart>
					</ResponsiveContainer>
				</div>
			</div>
		</div>
	);
};
