import { format, subDays } from "date-fns";
import { Calendar, Layout, Moon, Sun, ChevronDown, ChevronRight } from "lucide-react";
import React, { useState } from "react";
import {
	defaultSourceDisplayInfo,
	sourceDisplayInfo,
} from "../../config/sourceDisplayInfo";
import { WeatherWidget } from "../weather/WeatherWidget";

interface SidebarProps {
	selectedSource: string;
	setSelectedSource: (source: string) => void;
	selectedDate: Date;
	setSelectedDate: (date: Date) => void;
	darkMode: boolean;
	setDarkMode: (dark: boolean) => void;
	onMenuItemClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
	selectedSource,
	setSelectedSource,
	selectedDate,
	setSelectedDate,
	darkMode,
	setDarkMode,
	onMenuItemClick,
}) => {
	// グループ設定
	const sourceGroups = {
		default: [
			"arxiv",
			"github",
			"hacker-news",
			"tech-news",
			"business-news",
			"zenn",
			"qiita",
			"note",
			"reddit",
			"4chan",
			"5chan",
		],
		trendradar: ["trendradar-zhihu"],
	};

	// グループの開閉状態
	const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
		default: true,
		trendradar: true,
	});

	const toggleGroup = (group: string) => {
		setExpandedGroups((prev) => ({
			...prev,
			[group]: !prev[group],
		}));
	};

	return (
		<div className="sidebar-container h-full flex flex-col">
			{/* Header - 固定 */}
			<div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
				<div className="flex items-center space-x-2">
					<Layout className="w-5 h-5 md:w-6 md:h-6 text-blue-600 dark:text-blue-400" />
					<span className="text-lg md:text-xl font-bold text-gray-900 dark:text-white">
						Dashboard
					</span>
				</div>
			</div>

			{/* Weather Widget - 固定 */}
			<div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
				<WeatherWidget />
			</div>

			{/* Date Selector - 固定 */}
			<div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
				<div className="flex items-center space-x-2 mb-3">
					<Calendar className="w-4 h-4 md:w-5 md:h-5 text-gray-600 dark:text-gray-400" />
					<span className="font-medium text-gray-700 dark:text-gray-300">
						Select Date
					</span>
				</div>
				<input
					type="date"
					value={format(selectedDate, "yyyy-MM-dd")}
					max={format(new Date(), "yyyy-MM-dd")}
					min={format(subDays(new Date(), 30), "yyyy-MM-dd")}
					onChange={(e) => setSelectedDate(new Date(e.target.value))}
					className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-touch touch-manipulation"
				/>
			</div>

			{/* Navigation - スクロール可能 */}
			<nav className="flex-1 p-3 md:p-4 overflow-y-auto">
				{/* Sources Section */}
				{/* Sources Sections */}
				{Object.entries(sourceGroups).map(([groupKey, groupSources]) => (
					<div key={groupKey} className="mb-4">
						{/* Group Header */}
						{groupKey === "trendradar" && (
							<button
								onClick={() => toggleGroup(groupKey)}
								className="w-full flex items-center justify-between px-2 py-1 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
							>
								<span>TrendRadar</span>
								{expandedGroups[groupKey] ? (
									<ChevronDown className="w-4 h-4" />
								) : (
									<ChevronRight className="w-4 h-4" />
								)}
							</button>
						)}

						{/* Default group header (optional, mostly hidden or styled differently) */}
						{groupKey === "default" && (
							<button
								onClick={() => toggleGroup(groupKey)}
								className="w-full flex items-center justify-between px-2 py-1 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
							>
								<span>Feeds</span>
								{expandedGroups[groupKey] ? (
									<ChevronDown className="w-4 h-4" />
								) : (
									<ChevronRight className="w-4 h-4" />
								)}
							</button>
						)}

						{/* Sources List */}
						{expandedGroups[groupKey] && (
							<div className="space-y-1">
								{groupSources.map((source) => {
									const sourceInfo =
										sourceDisplayInfo[source] || defaultSourceDisplayInfo;
									return (
										<button
											key={source}
											onClick={() => {
												setSelectedSource(source);
												onMenuItemClick();
											}}
											className={`w-full text-left px-4 py-2 rounded-lg font-medium transition-colors min-h-touch touch-manipulation flex items-center ${selectedSource === source
												? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
												: "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30"
												}`}
										>
											{sourceInfo.title}
										</button>
									);
								})}
							</div>
						)}
					</div>
				))}

				{/* Theme Toggle */}
				<div className="mt-6">
					<div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
						Theme
					</div>
					<button
						onClick={() => setDarkMode(!darkMode)}
						className="w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/30 min-h-touch touch-manipulation"
					>
						<span>{darkMode ? "Light Mode" : "Dark Mode"}</span>
						{darkMode ? (
							<Sun className="w-5 h-5 text-yellow-500" />
						) : (
							<Moon className="w-5 h-5 text-blue-600" />
						)}
					</button>
				</div>
			</nav>
		</div>
	);
};
