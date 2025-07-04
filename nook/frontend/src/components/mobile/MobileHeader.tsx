import { ArrowLeft, Menu, MoreVertical, Search } from "lucide-react";
import type React from "react";

interface MobileHeaderProps {
	title: string;
	showBackButton?: boolean;
	showMenuButton?: boolean;
	showSearchButton?: boolean;
	onMenuClick?: () => void;
	onSearchClick?: () => void;
	onBackClick?: () => void;
	rightActions?: React.ReactNode;
}

export function MobileHeader({
	title,
	showBackButton = false,
	showMenuButton = true,
	showSearchButton = true,
	onMenuClick,
	onSearchClick,
	onBackClick,
	rightActions,
}: MobileHeaderProps) {
	return (
		<header className="mobile-header dark:bg-gray-900 dark:border-gray-700">
			<div className="flex items-center justify-between px-4 py-3">
				{/* Left Section */}
				<div className="flex items-center">
					{showBackButton && (
						<button
							onClick={onBackClick}
							className="btn-secondary p-2 mr-2"
							aria-label="戻る"
						>
							<ArrowLeft className="w-5 h-5" />
						</button>
					)}

					{showMenuButton && !showBackButton && (
						<button
							onClick={onMenuClick}
							className="btn-secondary p-2 mr-3"
							aria-label="メニューを開く"
						>
							<Menu className="w-5 h-5" />
						</button>
					)}

					<h1 className="text-responsive-lg font-bold text-gray-900 dark:text-white truncate">
						{title}
					</h1>
				</div>

				{/* Right Section */}
				<div className="flex items-center space-x-2">
					{showSearchButton && (
						<button
							onClick={onSearchClick}
							className="btn-secondary p-2"
							aria-label="検索"
						>
							<Search className="w-5 h-5" />
						</button>
					)}

					{rightActions || (
						<button
							className="btn-secondary p-2"
							aria-label="その他のオプション"
						>
							<MoreVertical className="w-5 h-5" />
						</button>
					)}
				</div>
			</div>
		</header>
	);
}
