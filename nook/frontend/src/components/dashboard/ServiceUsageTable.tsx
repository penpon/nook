import React from 'react';
import { ServiceUsage } from '../../hooks/useUsageData';

interface ServiceUsageTableProps {
  serviceUsage: ServiceUsage[];
}

export const ServiceUsageTable: React.FC<ServiceUsageTableProps> = ({
  serviceUsage
}) => {
  const formatNumber = (num: number) => num.toLocaleString();
  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ja-JP');
  };

  return (
    <div className="dashboard-container bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="cq-xs:p-4 cq-md:p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="cq-xs:text-base cq-md:text-lg font-semibold text-gray-900 dark:text-white">
          サービス別使用量
        </h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-left cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                サービス名
              </th>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                呼び出し
              </th>
              <th className="cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-md:table-cell">
                入力トークン
              </th>
              <th className="cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-md:table-cell">
                出力トークン
              </th>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                コスト
              </th>
              <th className="cq-lg:px-6 cq-lg:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-lg:table-cell">
                最終呼び出し
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {serviceUsage.map((service) => (
              <tr key={service.service} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap">
                  <span className="inline-flex items-center cq-xs:px-2 cq-xs:py-0.5 cq-md:px-2.5 cq-md:py-0.5 rounded-full cq-xs:text-xs cq-md:text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                    {service.service}
                  </span>
                </td>
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-900 dark:text-white font-medium">
                  {formatNumber(service.calls)}
                </td>
                <td className="cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-md:table-cell">
                  {formatNumber(service.inputTokens)}
                </td>
                <td className="cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-md:table-cell">
                  {formatNumber(service.outputTokens)}
                </td>
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm font-medium text-green-600 dark:text-green-400">
                  {formatCurrency(service.cost)}
                </td>
                <td className="cq-lg:px-6 cq-lg:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-lg:table-cell">
                  {formatDate(service.lastCalled)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};