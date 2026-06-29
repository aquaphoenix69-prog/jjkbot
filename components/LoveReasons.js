'use client';
import { useState } from 'react';
import { loveReasons } from '@/lib/digiPersona';

const loveGifs = [
  'https://media.giphy.com/media/l0HlGEX1ZORa0aIvu/giphy.gif',
  'https://media.giphy.com/media/xT0GqssRweIhlz209i/giphy.gif',
  'https://media.giphy.com/media/l4FGni1RBAR2OWsGk/giphy.gif',
  'https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif',
  'https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif',
  'https://media.giphy.com/media/l2Jhtd7mIBSguDKOk/giphy.gif',
  'https://media.giphy.com/media/3o7TKoWXm3okO1kgHC/giphy.gif',
  'https://media.giphy.com/media/xUPGcl3ijl0vBhMYdy/giphy.gif',
  'https://media.giphy.com/media/TGcD6N8uzJ3Uo/giphy.gif',
  'https://media.giphy.com/media/1lk1IcVgqPLkA/giphy.gif',
];

export default function LoveReasons() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const nextReason = () => {
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % loveReasons.length);
      setIsAnimating(false);
    }, 300);
  };

  const prevReason = () => {
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev - 1 + loveReasons.length) % loveReasons.length);
      setIsAnimating(false);
    }, 300);
  };

  return (
    <div className="glass-card rounded-2xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="text-center">
        <h2 className="text-xl sm:text-2xl font-bold neon-text">Reasons I Love You</h2>
        <p className="text-xs sm:text-sm text-gray-400 mt-1">
          #{currentIndex + 1} of {loveReasons.length} (and counting forever...)
        </p>
      </div>

      <div className="love-reason-card rounded-xl p-4 sm:p-6 min-h-[100px] flex flex-col items-center justify-center gap-3 sm:gap-4">
        <p
          className={`text-center text-sm sm:text-lg text-gray-200 leading-relaxed italic transition-all duration-300 ${
            isAnimating ? 'opacity-0 translate-y-4' : 'opacity-100 translate-y-0'
          }`}
        >
          &ldquo;{loveReasons[currentIndex]}&rdquo;
        </p>
        <img
          src={loveGifs[currentIndex % loveGifs.length]}
          alt="love gif"
          className={`w-32 h-24 sm:w-40 sm:h-32 object-cover rounded-lg opacity-80 transition-all duration-300 ${
            isAnimating ? 'opacity-0 scale-90' : 'opacity-80 scale-100'
          }`}
        />
      </div>

      <div className="flex items-center justify-center gap-3 sm:gap-4">
        <button
          onClick={prevReason}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-pink-500/30 flex items-center justify-center text-neon-rose hover:bg-pink-500/10 active:bg-pink-500/20 transition-all"
        >
          &larr;
        </button>
        <button
          onClick={nextReason}
          className="btn-love px-4 sm:px-6 py-2 sm:py-2.5 rounded-xl text-white font-medium text-xs sm:text-sm active:scale-95"
        >
          More love 💝
        </button>
        <button
          onClick={nextReason}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-pink-500/30 flex items-center justify-center text-neon-rose hover:bg-pink-500/10 active:bg-pink-500/20 transition-all"
        >
          &rarr;
        </button>
      </div>
    </div>
  );
}
