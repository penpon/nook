import { format } from "date-fns";
import { ja } from "date-fns/locale";
import type React from "react";
import {
	defaultSourceDisplayInfo,
	sourceDisplayInfo,
} from "../config/sourceDisplayInfo";

interface NewsHeaderProps {
	selectedSource: string;
	selectedDate: Date;
	darkMode: boolean;
}

export const NewsHeader: React.FC<NewsHeaderProps> = ({
	selectedSource,
	selectedDate,
	darkMode,
}) => {
	const sourceInfo =
		sourceDisplayInfo[selectedSource] || defaultSourceDisplayInfo;

	// 日付フォーマット（日本語ロケール対応）
	const formatDate = (date: Date, formatStr: string): string => {
		if (formatStr.includes("年")) {
			return format(date, formatStr, { locale: ja });
		}
		return format(date, formatStr);
	};

	const dateFormatted = formatDate(selectedDate, sourceInfo.dateFormat);

	return (
		<div className="mb-8">
			<div
				className={`
        rounded-xl shadow-lg p-8
        ${
					darkMode
						? "bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700"
						: `bg-gradient-to-r ${sourceInfo.gradientFrom || "from-blue-50"} ${sourceInfo.gradientTo || "to-indigo-50"} border ${sourceInfo.borderColor || "border-blue-200"}`
				}
        transition-all duration-300 hover:shadow-xl
      `}
			>
				<h1
					className={`
          text-4xl sm:text-5xl lg:text-6xl font-bold text-center mb-3
          ${darkMode ? "text-white" : "text-gray-900"}
        `}
				>
					{sourceInfo.title}
				</h1>
				<p
					className={`
          text-lg sm:text-xl text-center
          ${darkMode ? "text-gray-300" : "text-gray-600"}
        `}
				>
					{sourceInfo.subtitle} ({dateFormatted})
				</p>
			</div>
		</div>
	);
};
