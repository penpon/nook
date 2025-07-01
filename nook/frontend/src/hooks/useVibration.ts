'use client';

import { useCallback } from 'react';

export function useVibration() {
  const vibrate = useCallback((pattern: number | number[]) => {
    if (typeof window === 'undefined') return;
    
    if ('vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  }, []);
  
  const vibrateShort = useCallback(() => {
    vibrate(50);
  }, [vibrate]);
  
  const vibrateMedium = useCallback(() => {
    vibrate(100);
  }, [vibrate]);
  
  const vibrateLong = useCallback(() => {
    vibrate(200);
  }, [vibrate]);
  
  const vibratePattern = useCallback(() => {
    vibrate([100, 50, 100]);
  }, [vibrate]);
  
  return {
    vibrate,
    vibrateShort,
    vibrateMedium,
    vibrateLong,
    vibratePattern,
  };
}