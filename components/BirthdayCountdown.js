'use client';
import { useState, useEffect, useCallback } from 'react';

export default function BirthdayCountdown({ onCelebrate }) {
  const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 });
  const [isBirthday, setIsBirthday] = useState(false);

  const calculateTimeLeft = useCallback(() => {
    const now = new Date();
    const currentYear = now.getFullYear();
    let birthday = new Date(currentYear, 6, 15); // July 15 — update to Sena's actual birthday

    if (now > birthday) {
      birthday = new Date(currentYear + 1, 6, 15);
    }

    const diff = birthday - now;

    if (diff <= 0) {
      setIsBirthday(true);
      return { days: 0, hours: 0, minutes: 0, seconds: 0 };
    }

    return {
      days: Math.floor(diff / (1000 * 60 * 60 * 24)),
      hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((diff / (1000 * 60)) % 60),
      seconds: Math.floor((diff / 1000) % 60),
    };
  }, []);

  useEffect(() => {
    setTimeLeft(calculateTimeLeft());
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);
    return () => clearInterval(timer);
  }, [calculateTimeLeft]);

  return (
    <div className="glass-card rounded-2xl p-6 space-y-5">
      <div className="text-center">
        <h2 className="text-2xl font-bold neon-text">
          {isBirthday ? "HAPPY BIRTHDAY, MY LOVE!" : "Birthday Countdown"}
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          {isBirthday
            ? "Today is YOUR day, queen! 👑"
            : "Every second closer to celebrating YOU"}
        </p>
      </div>

      {!isBirthday && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { value: timeLeft.days, label: 'Days' },
            { value: timeLeft.hours, label: 'Hours' },
            { value: timeLeft.minutes, label: 'Mins' },
            { value: timeLeft.seconds, label: 'Secs' },
          ].map((item) => (
            <div key={item.label} className="countdown-digit rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-neon-pink">{String(item.value).padStart(2, '0')}</div>
              <div className="text-xs text-gray-400 mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {isBirthday && (
        <div className="text-center text-4xl animate-heart-beat">
          🎂🎉💕👑✨
        </div>
      )}

      <button
        onClick={onCelebrate}
        className="w-full btn-love py-3 rounded-xl text-white font-semibold text-sm animate-pulse-glow"
      >
        {isBirthday ? "CELEBRATE! 🎉🎊💕" : "Celebrate Early! 🎉"}
      </button>
    </div>
  );
}
