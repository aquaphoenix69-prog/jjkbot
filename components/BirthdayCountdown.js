'use client';
import { useState, useEffect } from 'react';

function checkIfBirthday() {
  const now = new Date();
  return now.getMonth() === 5 && now.getDate() === 30;
}

function getTimeUntilBirthday() {
  const now = new Date();
  const currentYear = now.getFullYear();
  let birthday = new Date(currentYear, 5, 30);

  if (now > birthday) {
    birthday = new Date(currentYear + 1, 5, 30);
  }

  const diff = birthday - now;
  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60),
  };
}

export default function BirthdayCountdown({ onCelebrate }) {
  const [isBirthday, setIsBirthday] = useState(true);
  const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 });

  useEffect(() => {
    const birthday = checkIfBirthday();
    setIsBirthday(birthday);

    if (!birthday) {
      setTimeLeft(getTimeUntilBirthday());
      const timer = setInterval(() => {
        setTimeLeft(getTimeUntilBirthday());
      }, 1000);
      return () => clearInterval(timer);
    }
  }, []);

  return (
    <div className="glass-card rounded-2xl p-6 space-y-5">
      <div className="text-center">
        <h2 className="text-2xl font-bold neon-text">
          {isBirthday ? "🎂 HAPPY 20TH BIRTHDAY, SENA! 🎂" : "Birthday Countdown"}
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          {isBirthday
            ? "TODAY IS YOUR DAY, QUEEN! 👑✨"
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
        <div className="text-center space-y-4">
          <div className="text-5xl animate-heart-beat">
            🎂🎉💕👑✨
          </div>
          <p className="text-lg text-gray-200 leading-relaxed">
            20 years of you making this world a better place. My beautiful girl is officially in her 20s and I couldn&apos;t be more proud to be yours. I love you endlessly, Sena. 💕
          </p>
          <img
            src="https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif"
            alt="birthday love"
            className="w-48 h-auto mx-auto rounded-xl opacity-90"
          />
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
