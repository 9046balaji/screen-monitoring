import { useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { checkDopamineLoop } from '../api/digiwell';

export default function useDopamineDetector() {
  const alertedRef = useRef(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const { detected, apps } = await checkDopamineLoop();
        if (detected && !alertedRef.current) {
          toast.error(`Dopamine Loop Detected! Rapid switching between: ${apps.slice(0,3).join(', ')}... Take a break!`, {
            duration: 6000,
            icon: '⚠️'
          });
          alertedRef.current = true;
          // Reset alert after an hour so we don't spam them constantly
          setTimeout(() => {
            alertedRef.current = false;
          }, 60 * 60 * 1000);
        } else if (!detected) {
            // Un-set if condition clears naturally to allow future checks
            alertedRef.current = false;
        }
      } catch (err) {
        console.error("Failed to check dopamine loop", err);
      }
    }, 15000); // Check every 15 seconds

    return () => clearInterval(interval);
  }, []);
}