// 画像遅延読み込み
export function createIntersectionObserver(
  callback: (entries: IntersectionObserverEntry[]) => void,
  options?: IntersectionObserverInit
) {
  if (typeof window === 'undefined') return null;
  
  return new IntersectionObserver(callback, {
    rootMargin: '50px',
    threshold: 0.1,
    ...options,
  });
}

// バッテリー情報取得
export async function getBatteryInfo(): Promise<{
  level: number;
  charging: boolean;
  dischargingTime: number;
} | null> {
  if (typeof window === 'undefined') return null;
  
  try {
    // @ts-ignore - Battery API is experimental
    const battery = await navigator.getBattery?.();
    if (!battery) return null;
    
    return {
      level: battery.level,
      charging: battery.charging,
      dischargingTime: battery.dischargingTime,
    };
  } catch {
    return null;
  }
}

// ネットワーク状況取得
export function getNetworkInfo(): {
  effectiveType: string;
  downlink: number;
  saveData: boolean;
} | null {
  if (typeof window === 'undefined') return null;
  
  // @ts-ignore - Network Information API
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  
  if (!connection) return null;
  
  return {
    effectiveType: connection.effectiveType || 'unknown',
    downlink: connection.downlink || 0,
    saveData: connection.saveData || false,
  };
}

// 省電力モード検出
export async function isPowerSaverMode(): Promise<boolean> {
  const battery = await getBatteryInfo();
  const network = getNetworkInfo();
  
  // バッテリー残量が少ない、または省データモード
  return (
    (battery && battery.level < 0.2 && !battery.charging) ||
    (network && network.saveData) ||
    false
  );
}

// FPS制限（省電力時）
export function requestAnimationFrameThrottled(
  callback: FrameRequestCallback,
  throttle: boolean = false
): number {
  if (throttle) {
    // 30 FPS に制限
    let lastTime = 0;
    const targetInterval = 1000 / 30;
    
    const throttledCallback: FrameRequestCallback = (time) => {
      if (time - lastTime >= targetInterval) {
        callback(time);
        lastTime = time;
      } else {
        requestAnimationFrame(throttledCallback);
      }
    };
    
    return requestAnimationFrame(throttledCallback);
  }
  
  return requestAnimationFrame(callback);
}

// メモリ使用量監視
export function getMemoryInfo(): {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
} | null {
  if (typeof window === 'undefined') return null;
  
  // @ts-ignore - performance.memory は実験的
  const memory = performance.memory;
  
  if (!memory) return null;
  
  return {
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
  };
}

// レンダリング最適化
export async function shouldReduceAnimations(): Promise<boolean> {
  if (typeof window === 'undefined') return false;
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isPowerSaver = await isPowerSaverMode();
  
  return prefersReducedMotion || isPowerSaver;
}