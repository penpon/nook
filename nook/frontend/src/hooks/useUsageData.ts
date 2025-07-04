import axios from "axios";
import { useEffect, useState } from "react";

export interface UsageSummary {
	todayTokens: number;
	todayCost: number;
	monthCost: number;
	totalCalls: number;
}

export interface ServiceUsage {
	service: string;
	calls: number;
	inputTokens: number;
	outputTokens: number;
	cost: number;
	lastCalled: string;
}

export interface DailyUsage {
	date: string;
	services: { [key: string]: number };
	totalCost: number;
}

export function useUsageData() {
	const [summary, setSummary] = useState<UsageSummary | null>(null);
	const [serviceUsage, setServiceUsage] = useState<ServiceUsage[]>([]);
	const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

	const fetchData = async () => {
		try {
			setLoading(true);
			setError(null);

			const [summaryResponse, serviceResponse, dailyResponse] =
				await Promise.all([
					axios.get("http://localhost:8000/api/usage/summary"),
					axios.get("http://localhost:8000/api/usage/by-service"),
					axios.get("http://localhost:8000/api/usage/daily?days=30"),
				]);

			setSummary(summaryResponse.data);
			setServiceUsage(serviceResponse.data);
			setDailyUsage(dailyResponse.data);
			setLastUpdated(new Date());
		} catch (error) {
			console.error("データの取得に失敗しました:", error);
			setError("データの取得に失敗しました");

			// フォールバック用のモックデータ
			setSummary({
				todayTokens: 15420,
				todayCost: 0.23,
				monthCost: 12.45,
				totalCalls: 78,
			});
			setServiceUsage([
				{
					service: "OpenAI GPT-4",
					calls: 25,
					inputTokens: 8500,
					outputTokens: 3200,
					cost: 0.15,
					lastCalled: "2024-01-20T15:30:00Z",
				},
				{
					service: "Claude-3",
					calls: 18,
					inputTokens: 6200,
					outputTokens: 2800,
					cost: 0.08,
					lastCalled: "2024-01-20T14:45:00Z",
				},
			]);
			setDailyUsage([
				{
					date: "2024-01-15",
					services: { "OpenAI GPT-4": 0.12, "Claude-3": 0.08 },
					totalCost: 0.2,
				},
				{
					date: "2024-01-16",
					services: { "OpenAI GPT-4": 0.18, "Claude-3": 0.06 },
					totalCost: 0.24,
				},
				{
					date: "2024-01-17",
					services: { "OpenAI GPT-4": 0.15, "Claude-3": 0.09 },
					totalCost: 0.24,
				},
				{
					date: "2024-01-18",
					services: { "OpenAI GPT-4": 0.22, "Claude-3": 0.07 },
					totalCost: 0.29,
				},
				{
					date: "2024-01-19",
					services: { "OpenAI GPT-4": 0.19, "Claude-3": 0.11 },
					totalCost: 0.3,
				},
				{
					date: "2024-01-20",
					services: { "OpenAI GPT-4": 0.15, "Claude-3": 0.08 },
					totalCost: 0.23,
				},
			]);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchData();

		// 5分ごとの自動更新
		const interval = setInterval(fetchData, 5 * 60 * 1000);
		return () => clearInterval(interval);
	}, []);

	return {
		summary,
		serviceUsage,
		dailyUsage,
		loading,
		error,
		lastUpdated,
		refetch: fetchData,
	};
}
