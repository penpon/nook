import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
	readonly platforms: string[];
	readonly userChoice: Promise<{
		outcome: "accepted" | "dismissed";
		platform: string;
	}>;
	prompt(): Promise<void>;
}

export function useInstallPrompt() {
	const [deferredPrompt, setDeferredPrompt] =
		useState<BeforeInstallPromptEvent | null>(null);
	const [isInstallable, setIsInstallable] = useState(false);

	useEffect(() => {
		const handler = (e: BeforeInstallPromptEvent) => {
			e.preventDefault();
			setDeferredPrompt(e);
			setIsInstallable(true);
		};

		window.addEventListener("beforeinstallprompt", handler as EventListener);

		return () => {
			window.removeEventListener(
				"beforeinstallprompt",
				handler as EventListener,
			);
		};
	}, []);

	const promptInstall = async () => {
		if (!deferredPrompt) return;

		deferredPrompt.prompt();
		const { outcome } = await deferredPrompt.userChoice;

		if (outcome === "accepted") {
			setDeferredPrompt(null);
			setIsInstallable(false);
		}
	};

	return {
		isInstallable,
		promptInstall,
	};
}
