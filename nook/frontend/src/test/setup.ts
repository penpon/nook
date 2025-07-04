import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach, expect, vi } from "vitest";
import axios from "axios";
import { mockWeatherResponse, mockHackerNewsResponse } from "./mocks/mockData";

// axiosのモック（最上位でホイスティング）
vi.mock("axios", () => ({
	default: {
		get: vi.fn(),
		create: vi.fn(() => ({
			get: vi.fn()
		}))
	}
}));

// テスト後のクリーンアップ
afterEach(() => {
	cleanup();
});

// window.matchMediaのモック
Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: vi.fn().mockImplementation((query) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(), // deprecated
		removeListener: vi.fn(), // deprecated
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn(),
	})),
});

// localStorageのモック
Object.defineProperty(window, "localStorage", {
	value: {
		getItem: vi.fn(() => null),
		setItem: vi.fn(() => null),
		removeItem: vi.fn(() => null),
		clear: vi.fn(() => null),
	},
	writable: true,
});

// window.scrollToのモック
Object.defineProperty(window, "scrollTo", {
	value: vi.fn(),
	writable: true,
});

// URL操作の制限回避
Object.defineProperty(window, "location", {
	value: {
		href: "http://localhost:3000/",
		origin: "http://localhost:3000",
		pathname: "/",
		search: "",
		hash: ""
	},
	writable: true,
});

// APIモックの設定
const mockedAxios = vi.mocked(axios);

// APIレスポンスのモック実装
const mockApiResponse = (url: string, config?: any) => {
	
	if (url === '/weather') {
		return Promise.resolve({
			data: mockWeatherResponse,
			status: 200,
			statusText: 'OK'
		});
	}
	
	if (url === '/content/hacker-news' || url.startsWith('/content/hacker-news')) {
		return Promise.resolve({
			data: mockHackerNewsResponse,
			status: 200,
			statusText: 'OK'
		});
	}
	
	return Promise.reject(new Error(`Mock not implemented for ${url}`));
};

// axios.getのモック設定
mockedAxios.get.mockImplementation(mockApiResponse);

// より詳細なモックインスタンス
const mockAxiosInstance = {
	get: vi.fn().mockImplementation(mockApiResponse),
	interceptors: {
		request: {
			use: vi.fn(() => mockAxiosInstance)
		},
		response: {
			use: vi.fn(() => mockAxiosInstance)
		}
	}
};

// axios.createから返されるインスタンスのモック設定
mockedAxios.create.mockImplementation(() => {
	return mockAxiosInstance;
});

// カスタムマッチャーの設定
expect.extend({});
