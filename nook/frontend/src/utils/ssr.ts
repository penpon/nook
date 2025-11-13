import React from "react";

export const isServer = typeof window === "undefined";
export const isClient = !isServer;

// SSR対応のuseEffect
export function useIsomorphicLayoutEffect(
	effect: React.EffectCallback,
	deps?: React.DependencyList,
) {
	if (isServer) {
		return;
	}

	React.useLayoutEffect(effect, deps);
}

// SSR対応のLocalStorage
export const storage = {
	getItem: (key: string): string | null => {
		if (isServer) return null;
		return localStorage.getItem(key);
	},

	setItem: (key: string, value: string): void => {
		if (isServer) return;
		localStorage.setItem(key, value);
	},

	removeItem: (key: string): void => {
		if (isServer) return;
		localStorage.removeItem(key);
	},
};

// SSR対応のwindowサイズ取得
export function useWindowSize() {
	const [size, setSize] = React.useState({
		width: isServer ? 1024 : window.innerWidth,
		height: isServer ? 768 : window.innerHeight,
	});

	React.useEffect(() => {
		if (isServer) return;

		const handleResize = () => {
			setSize({
				width: window.innerWidth,
				height: window.innerHeight,
			});
		};

		window.addEventListener("resize", handleResize);
		return () => window.removeEventListener("resize", handleResize);
	}, []);

	return size;
}
