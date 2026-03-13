import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';

export default function use2020Timer() {
  const timerRef = useRef(null);

  useEffect(() => {
    // Defines the 20 minute interval for the 20-20-20 rule
    const TWENTY_MINUTES = 20 * 60 * 1000;

    const showNotification = () => {
      toast('Look 20 feet away for 20 seconds', {
        icon: '👀',
        duration: 20000, // keep the toast visible for the 20 seconds
        style: {
          borderRadius: '10px',
          background: '#1E293B',
          color: '#fff',
          border: '2px solid #3b82f6',
          fontSize: '16px',
          padding: '16px',
        },
      });
    };

    // Set up the recurring interval
    timerRef.current = setInterval(() => {
      showNotification();
    }, TWENTY_MINUTES);

    // Track active usage: reset timer on system events if we wanted to get fancy
    // but the requirement says "timer during active usage" 
    // We treat the app being open as active usage for this feature.
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);
}