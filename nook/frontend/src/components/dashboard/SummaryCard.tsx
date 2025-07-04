import type React from "react";

interface SummaryCardProps {
	title: string;
	value: string;
	icon: React.ReactNode;
	colorClass: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
	title,
	value,
	icon,
	colorClass,
}) => {
	return (
		<div className="card-container bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
			<div className="cq-xs:p-4 cq-md:p-6">
				{/* コンテナサイズに応じたレイアウト変更 */}
				<div className="cq-xs:flex cq-xs:flex-col cq-sm:flex-row cq-sm:items-center cq-sm:justify-between">
					<div className="flex-1">
						<p className="cq-xs:text-xs cq-md:text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
							{title}
						</p>
						<p
							className={`cq-xs:text-lg cq-md:text-2xl cq-lg:text-3xl font-bold ${colorClass}`}
						>
							{value}
						</p>
					</div>
					<div
						className={`cq-xs:mt-2 cq-sm:mt-0 cq-xs:self-end cq-sm:self-auto cq-xs:p-2 cq-md:p-3 rounded-full bg-opacity-10 ${colorClass.replace("text-", "bg-")}`}
					>
						<div
							className={`cq-xs:w-5 cq-xs:h-5 cq-md:w-6 cq-md:h-6 ${colorClass}`}
						>
							{icon}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
};
