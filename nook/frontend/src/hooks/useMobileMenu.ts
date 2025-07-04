import { useEffect, useState } from "react";

export function useMobileMenu() {
	const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
	const [scrollPosition, setScrollPosition] = useState(0);

	useEffect(() => {
		if (isMobileMenuOpen) {
			const currentScrollY = window.scrollY;
			setScrollPosition(currentScrollY);

			document.body.style.overflow = "hidden";
			document.body.style.position = "fixed";
			document.body.style.top = `-${currentScrollY}px`;
			document.body.style.width = "100%";
		} else {
			document.body.style.overflow = "";
			document.body.style.position = "";
			document.body.style.top = "";
			document.body.style.width = "";

			window.scrollTo(0, scrollPosition);
		}

		return () => {
			document.body.style.overflow = "";
			document.body.style.position = "";
			document.body.style.top = "";
			document.body.style.width = "";
		};
	}, [isMobileMenuOpen, scrollPosition]);

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
