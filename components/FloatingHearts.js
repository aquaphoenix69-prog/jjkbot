'use client';
import { useEffect, useState } from 'react';

export default function FloatingHearts() {
  const [hearts, setHearts] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const id = Date.now() + Math.random();
      const heart = {
        id,
        left: Math.random() * 100,
        size: 12 + Math.random() * 20,
        opacity: 0.3 + Math.random() * 0.4,
        duration: 3 + Math.random() * 3,
      };
      setHearts(prev => [...prev.slice(-15), heart]);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const cleanup = setInterval(() => {
      setHearts(prev => prev.slice(-10));
    }, 5000);
    return () => clearInterval(cleanup);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {hearts.map(heart => (
        <div
          key={heart.id}
          className="floating-heart"
          style={{
            left: `${heart.left}%`,
            bottom: '-50px',
            fontSize: `${heart.size}px`,
            opacity: heart.opacity,
            animationDuration: `${heart.duration}s`,
          }}
        >
          💕
        </div>
      ))}
    </div>
  );
}
