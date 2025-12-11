import type React from "react";
import { usePWA } from "../hooks/usePWA";

export const PWAUpdateNotification: React.FC = () => {
	const { needRefresh, offlineReady, updateServiceWorker, close } = usePWA();

	if (!needRefresh && !offlineReady) return null;

	return (
		<div className="fixed bottom-4 right-4 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 max-w-sm">
			{offlineReady && (
				<div className="mb-2">
					<p className="text-sm text-gray-700 dark:text-gray-300">
						アプリがオフラインで利用可能になりました！
					</p>
				</div>
			)}

			{needRefresh && (
				<div className="mb-2">
					<p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
						新しいバージョンが利用可能です。更新しますか？
					</p>
					<div className="flex space-x-2">
						<button
							onClick={() => updateServiceWorker(true)}
							className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 touch-manipulation"
						>
							更新
						</button>
						<button
							onClick={close}
							className="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-sm hover:bg-gray-400 dark:hover:bg-gray-500 touch-manipulation"
						>
							後で
						</button>
					</div>
				</div>
			)}

			{!needRefresh && offlineReady && (
				<button
					onClick={close}
					className="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-sm hover:bg-gray-400 dark:hover:bg-gray-500 touch-manipulation"
				>
					閉じる
				</button>
			)}
		</div>
	);
};
