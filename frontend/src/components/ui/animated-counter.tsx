'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { cn, formatNumber } from '@/lib/utils';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  className?: string;
  format?: boolean;
}

export function AnimatedCounter({ value, duration = 600, className, format = true }: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const ref = useRef({ start: 0, end: value, startTime: 0 });
  const frameRef = useRef<number>();

  useEffect(() => {
    ref.current = { start: displayValue, end: value, startTime: performance.now() };

    const animate = (now: number) => {
      const elapsed = now - ref.current.startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = ref.current.start + (ref.current.end - ref.current.start) * eased;
      setDisplayValue(Math.round(current));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [value, duration]);

  const display = format ? formatNumber(displayValue) : String(displayValue);

  return (
    <motion.span
      className={cn('tabular-nums', className)}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {display}
    </motion.span>
  );
}
