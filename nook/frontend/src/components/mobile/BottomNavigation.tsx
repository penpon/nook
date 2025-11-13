import { Home, Search, TrendingUp, User } from "lucide-react";
import type React from "react";
import { useVibration } from "../../hooks/useVibration";

interface NavItem {
	icon: React.ComponentType<{ className?: string }>;
	label: string;
	sourceId?: string;
	pageId?: string;
}

interface BottomNavigationProps {
	selectedSource: string;
	setSelectedSource: (source: string) => void;
	currentPage: string;
	setCurrentPage: (page: string) => void;
}

const navItems: NavItem[] = [
	{ icon: Home, label: "ホーム", sourceId: "hacker-news", pageId: "content" },
	{
		icon: TrendingUp,
		label: "トレンド",
		sourceId: "github",
		pageId: "content",
	},
	{ icon: Search, label: "検索", pageId: "search" },
	{ icon: User, label: "設定", pageId: "settings" },
];

export function BottomNavigation({
	selectedSource,
	setSelectedSource,
	currentPage,
	setCurrentPage,
}: BottomNavigationProps) {
	const { vibrateShort } = useVibration();

	const handleNavigation = (item: NavItem) => {
		vibrateShort();

		if (item.sourceId) {
			setSelectedSource(item.sourceId);
			setCurrentPage("content");
		} else if (item.pageId) {
			setCurrentPage(item.pageId);
		}
	};

	const isActive = (item: NavItem) => {
		if (item.sourceId && currentPage === "content") {
			return selectedSource === item.sourceId;
		}
		return currentPage === item.pageId;
	};

	return (
		<nav className="mobile-nav dark:bg-gray-900 dark:border-gray-700">
			{navItems.map((item) => {
				const Icon = item.icon;
				const active = isActive(item);

				return (
					<button
						key={item.label}
						onClick={() => handleNavigation(item)}
						className={`
              flex flex-col items-center justify-center
              min-h-touch min-w-touch
              rounded-lg transition-colors duration-200
              touch-manipulation
              ${
								active
									? "text-blue-600 dark:text-blue-400"
									: "text-gray-600 dark:text-gray-400"
							}
              active:scale-95 active:bg-gray-100 dark:active:bg-gray-800
            `}
						aria-label={item.label}
					>
						<Icon className="w-6 h-6 mb-1" />
						<span className="text-xs font-medium">{item.label}</span>
					</button>
				);
			})}
		</nav>
	);
}
