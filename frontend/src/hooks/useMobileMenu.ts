import { useEffect, useState } from "react";

export function useMobileMenu() {
	const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

	useEffect(() => {
		if (isMobileMenuOpen) {
			// バックグラウンドスクロール防止（サイドバー内は許可）
			document.documentElement.style.overflow = "hidden";
			document.body.style.overflow = "hidden";
			// position: fixedは使用しない
		} else {
			// スクロール復元
			document.documentElement.style.overflow = "";
			document.body.style.overflow = "";
		}

		return () => {
			document.documentElement.style.overflow = "";
			document.body.style.overflow = "";
		};
	}, [isMobileMenuOpen]);

	const toggleMobileMenu = () => {
		setIsMobileMenuOpen(prev => !prev);
	};

	const closeMobileMenu = () => {
		setIsMobileMenuOpen(false);
	};

	const openMobileMenu = () => {
		setIsMobileMenuOpen(true);
	};

	return {
		isMobileMenuOpen,
		setIsMobileMenuOpen,
		toggleMobileMenu,
		closeMobileMenu,
		openMobileMenu,
	};
}
