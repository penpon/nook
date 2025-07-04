import { AlertTriangle, Bug, Home, RefreshCw } from "lucide-react";
import type React from "react";
import { Component, type ReactNode } from "react";

interface Props {
	children: ReactNode;
	fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
	onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
	hasError: boolean;
	error: Error | null;
	errorInfo: React.ErrorInfo | null;
	eventId: string | null;
}

interface ErrorDetails {
	message: string;
	stack?: string;
	componentStack?: string;
	timestamp: string;
	userAgent: string;
	url: string;
}

export class ErrorBoundary extends Component<Props, State> {
	private retryCount = 0;
	private readonly maxRetries = 3;

	constructor(props: Props) {
		super(props);
		this.state = {
			hasError: false,
			error: null,
			errorInfo: null,
			eventId: null,
		};
	}

	static getDerivedStateFromError(error: Error): Partial<State> {
		// Update state so the next render will show the fallback UI
		return {
			hasError: true,
			error,
			eventId: `error_${Date.now()}_${Math.random().toString(36).substring(2)}`,
		};
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
		// Store detailed error information
		this.setState({
			errorInfo,
		});

		// Create detailed error information
		const errorDetails: ErrorDetails = {
			message: error.message,
			stack: error.stack,
			componentStack: errorInfo.componentStack,
			timestamp: new Date().toISOString(),
			userAgent: navigator.userAgent,
			url: window.location.href,
		};

		// Log error details
		this.logError(error, errorDetails);

		// Call custom error handler if provided
		if (this.props.onError) {
			this.props.onError(error, errorInfo);
		}

		// Report to external error tracking service if needed
		// Example: Sentry.captureException(error, { extra: errorDetails });
	}

	private logError = (error: Error, details: ErrorDetails) => {
		console.group("🚨 React Error Boundary");
		console.error("Error:", error.message);
		console.error("Stack:", error.stack);
		console.error("Component Stack:", details.componentStack);
		console.error("Error Details:", details);
		console.groupEnd();
	};

	private resetError = () => {
		this.retryCount += 1;
		this.setState({
			hasError: false,
			error: null,
			errorInfo: null,
			eventId: null,
		});
	};

	private handleReload = () => {
		window.location.reload();
	};

	private handleGoHome = () => {
		window.location.href = "/";
	};

	private handleReportBug = () => {
		const { error, errorInfo } = this.state;
		const errorDetails = {
			message: error?.message,
			stack: error?.stack,
			componentStack: errorInfo?.componentStack,
			timestamp: new Date().toISOString(),
			url: window.location.href,
		};

		// Create mailto link with error details
		const subject = encodeURIComponent("Error Report - Nook Dashboard");
		const body = encodeURIComponent(`
Error Details:
${JSON.stringify(errorDetails, null, 2)}

Please describe what you were doing when this error occurred:
`);

		window.open(`mailto:support@example.com?subject=${subject}&body=${body}`);
	};

	render() {
		if (this.state.hasError) {
			// Use custom fallback if provided
			if (this.props.fallback) {
				const FallbackComponent = this.props.fallback;
				return (
					<FallbackComponent
						error={this.state.error!}
						resetError={this.resetError}
					/>
				);
			}

			// Default error UI
			const isDevelopment = import.meta.env.DEV;
			const { error, errorInfo, eventId } = this.state;

			return (
				<div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
					<div className="max-w-lg w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
						{/* Error Icon */}
						<div className="flex justify-center mb-6">
							<div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
								<AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
							</div>
						</div>

						{/* Error Title */}
						<h1 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-4">
							アプリケーションエラー
						</h1>

						{/* Error Message */}
						<p className="text-gray-600 dark:text-gray-300 text-center mb-6">
							申し訳ございません。予期しないエラーが発生しました。
							{this.retryCount > 0 && (
								<span className="block text-sm mt-2 text-orange-600 dark:text-orange-400">
									再試行回数: {this.retryCount}/{this.maxRetries}
								</span>
							)}
						</p>

						{/* Development Error Details */}
						{isDevelopment && error && (
							<div className="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
								<h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
									開発者向け情報:
								</h3>
								<p className="text-xs text-red-600 dark:text-red-400 font-mono mb-2">
									{error.message}
								</p>
								{errorInfo?.componentStack && (
									<details className="text-xs text-gray-600 dark:text-gray-400">
										<summary className="cursor-pointer hover:text-gray-800 dark:hover:text-gray-200">
											コンポーネントスタック
										</summary>
										<pre className="mt-2 whitespace-pre-wrap font-mono bg-white dark:bg-gray-800 p-2 rounded">
											{errorInfo.componentStack}
										</pre>
									</details>
								)}
								{eventId && (
									<p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
										Error ID: {eventId}
									</p>
								)}
							</div>
						)}

						{/* Action Buttons */}
						<div className="space-y-3">
							{/* Retry Button */}
							{this.retryCount < this.maxRetries && (
								<button
									onClick={this.resetError}
									className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200"
								>
									<RefreshCw className="w-4 h-4 mr-2" />
									再試行
								</button>
							)}

							{/* Reload Button */}
							<button
								onClick={this.handleReload}
								className="w-full flex items-center justify-center px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors duration-200"
							>
								<RefreshCw className="w-4 h-4 mr-2" />
								ページを再読み込み
							</button>

							{/* Home Button */}
							<button
								onClick={this.handleGoHome}
								className="w-full flex items-center justify-center px-4 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors duration-200"
							>
								<Home className="w-4 h-4 mr-2" />
								ホームに戻る
							</button>

							{/* Report Bug Button */}
							<button
								onClick={this.handleReportBug}
								className="w-full flex items-center justify-center px-4 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors duration-200"
							>
								<Bug className="w-4 h-4 mr-2" />
								バグを報告
							</button>
						</div>

						{/* Additional Info */}
						<div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-600">
							<p className="text-xs text-gray-500 dark:text-gray-400 text-center">
								問題が継続する場合は、ブラウザのキャッシュをクリアするか、
								開発者にお問い合わせください。
							</p>
						</div>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}

// Convenience wrapper with TypeScript support
// eslint-disable-next-line react-refresh/only-export-components
export const withErrorBoundary = <P extends object>(
	Component: React.ComponentType<P>,
	fallback?: React.ComponentType<{ error: Error; resetError: () => void }>,
	onError?: (error: Error, errorInfo: React.ErrorInfo) => void,
) => {
	const WrappedComponent = (props: P) => (
		<ErrorBoundary fallback={fallback} onError={onError}>
			<Component {...props} />
		</ErrorBoundary>
	);

	WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
	return WrappedComponent;
};

export default ErrorBoundary;
