import { vi } from "vitest";
import axios from "axios";
import { mockWeatherResponse, mockHackerNewsResponse } from "./mockData";

// axiosのモック設定
export const setupAxiosMocks = () => {
	// axios.get のモック実装
	const axiosGetMock = vi.fn((url: string) => {
		if (url === '/api/weather') {
			return Promise.resolve({
				data: mockWeatherResponse,
				status: 200,
				statusText: 'OK'
			});
		}
		
		if (url === '/api/content/hacker-news') {
			return Promise.resolve({
				data: mockHackerNewsResponse,
				status: 200,
				statusText: 'OK'
			});
		}
		
		// その他のURLの場合はエラーを投げる
		return Promise.reject(new Error(`Mock not implemented for ${url}`));
	});

	// axiosのgetメソッドを直接モック
	vi.mocked(axios.get).mockImplementation(axiosGetMock);

	return { axiosGetMock };
};