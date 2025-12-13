import { WifiOff } from 'lucide-react';
import type React from 'react';

export const OfflineFallback: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center p-8">
        <WifiOff className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">オフラインです</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          インターネット接続を確認してください
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 touch-manipulation"
        >
          再試行
        </button>
      </div>
    </div>
  );
};
