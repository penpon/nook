'use client';

import { useCallback, useRef } from 'react';

interface TouchGesture {
  deltaX: number;
  deltaY: number;
  distance: number;
  direction: 'left' | 'right' | 'up' | 'down' | 'none';
  velocity: number;
  duration: number;
}

interface UseTouchOptions {
  onSwipe?: (gesture: TouchGesture) => void;
  onTap?: (event: TouchEvent) => void;
  onLongPress?: (event: TouchEvent) => void;
  threshold?: number;
  longPressDelay?: number;
}

export function useTouch({
  onSwipe,
  onTap,
  onLongPress,
  threshold = 50,
  longPressDelay = 500,
}: UseTouchOptions = {}) {
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleTouchStart = useCallback(
    (event: TouchEvent) => {
      const touch = event.touches[0];
      touchStart.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };

      // Long press timer
      if (onLongPress) {
        longPressTimer.current = setTimeout(() => {
          onLongPress(event);
        }, longPressDelay);
      }
    },
    [onLongPress, longPressDelay]
  );

  const handleTouchEnd = useCallback(
    (event: TouchEvent) => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current);
        longPressTimer.current = null;
      }

      if (!touchStart.current) return;

      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - touchStart.current.x;
      const deltaY = touch.clientY - touchStart.current.y;
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
      const duration = Date.now() - touchStart.current.time;
      const velocity = distance / duration;

      // Tap detection
      if (distance < threshold && duration < 200 && onTap) {
        onTap(event);
        return;
      }

      // Swipe detection
      if (distance >= threshold && onSwipe) {
        let direction: TouchGesture['direction'] = 'none';

        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          direction = deltaX > 0 ? 'right' : 'left';
        } else {
          direction = deltaY > 0 ? 'down' : 'up';
        }

        onSwipe({
          deltaX,
          deltaY,
          distance,
          direction,
          velocity,
          duration,
        });
      }

      touchStart.current = null;
    },
    [onSwipe, onTap, threshold]
  );

  const handleTouchMove = useCallback(() => {
    // Clear long press on move
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  const touchHandlers = {
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
    onTouchMove: handleTouchMove,
  };

  return touchHandlers;
}
