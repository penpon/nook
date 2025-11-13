import { useRegisterSW } from "virtual:pwa-register/react";
import { useEffect, useState } from "react";

export function usePWA() {
	const [needRefresh, setNeedRefresh] = useState(false);
	const [offlineReady, setOfflineReady] = useState(false);

	const {
		needRefresh: [needRefreshSW, setNeedRefreshSW],
		offlineReady: [offlineReadySW, setOfflineReadySW],
		updateServiceWorker,
	} = useRegisterSW({
		onRegistered(r) {
			console.log("SW Registered: " + r);
		},
		onRegisterError(error) {
			console.log("SW registration error", error);
		},
	});

	useEffect(() => {
		setNeedRefresh(needRefreshSW);
	}, [needRefreshSW]);

	useEffect(() => {
		setOfflineReady(offlineReadySW);
	}, [offlineReadySW]);

	const close = () => {
		setOfflineReady(false);
		setNeedRefresh(false);
		setOfflineReadySW(false);
		setNeedRefreshSW(false);
	};

	return {
		needRefresh,
		offlineReady,
		updateServiceWorker,
		close,
	};
}
