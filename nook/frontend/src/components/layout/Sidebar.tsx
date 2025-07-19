import { format, subDays } from "date-fns";
import { Calendar, Layout, Moon, Sun } from "lucide-react";
import type React from "react";
import {
	defaultSourceDisplayInfo,
	sourceDisplayInfo,
} from "../../config/sourceDisplayInfo";
import { WeatherWidget } from "../weather/WeatherWidget";

interface SidebarProps {
	selectedSource: string;
	setSelectedSource: (source: string) => void;
	currentPage: string;
	setCurrentPage: (page: string) => void;
	selectedDate: Date;
	setSelectedDate: (date: Date) => void;
	darkMode: boolean;
	setDarkMode: (dark: boolean) => void;
	onMenuItemClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
	selectedSource,
	setSelectedSource,
	currentPage,
	setCurrentPage,
	selectedDate,
	setSelectedDate,
	darkMode,
	setDarkMode,
	onMenuItemClick,
}) => {
	const sources = [
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
		"penpon",
	];

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
				{/* Dashboard Section */}
				<div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
					Dashboard
				</div>
				<button
					onClick={() => {
						setCurrentPage("usage-dashboard");
						onMenuItemClick();
					}}
					className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${
						currentPage === "usage-dashboard"
							? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
							: "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30"
					}`}
				>
					Usage Dashboard
				</button>

				{/* Sources Section */}
				<div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400 mt-6">
					Sources
				</div>
				{sources.map((source) => {
					const sourceInfo =
						sourceDisplayInfo[source] || defaultSourceDisplayInfo;
					
					// 外部リンクの場合
					if (sourceInfo.externalUrl) {
						return (
							<button
								key={source}
								onClick={() => {
									window.location.href = sourceInfo.externalUrl;
								}}
								className="w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30"
							>
								{sourceInfo.title}
							</button>
						);
					}
					
					// 内部ソースの場合
					return (
						<button
							key={source}
							onClick={() => {
								setSelectedSource(source);
								setCurrentPage("content");
								onMenuItemClick();
							}}
							className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${
								selectedSource === source && currentPage === "content"
									? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
									: "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30"
							}`}
						>
							{sourceInfo.title}
						</button>
					);
				})}

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
