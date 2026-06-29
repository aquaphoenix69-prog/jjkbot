'use client';
import { useState } from 'react';
import { loveReasons } from '@/lib/digiPersona';

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
    <div className="glass-card rounded-2xl p-6 space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold neon-text">Reasons I Love You</h2>
        <p className="text-sm text-gray-400 mt-1">
          #{currentIndex + 1} of {loveReasons.length} (and counting forever...)
        </p>
      </div>

      <div className="love-reason-card rounded-xl p-6 min-h-[120px] flex items-center justify-center">
        <p
          className={`text-center text-lg text-gray-200 leading-relaxed italic transition-all duration-300 ${
            isAnimating ? 'opacity-0 translate-y-4' : 'opacity-100 translate-y-0'
          }`}
        >
          &ldquo;{loveReasons[currentIndex]}&rdquo;
        </p>
      </div>

      <div className="flex items-center justify-center gap-4">
        <button
          onClick={prevReason}
          className="w-10 h-10 rounded-full border border-pink-500/30 flex items-center justify-center text-neon-rose hover:bg-pink-500/10 transition-all"
        >
          &larr;
        </button>
        <button
          onClick={nextReason}
          className="btn-love px-6 py-2.5 rounded-xl text-white font-medium text-sm"
        >
          Show me more love 💝
        </button>
        <button
          onClick={nextReason}
          className="w-10 h-10 rounded-full border border-pink-500/30 flex items-center justify-center text-neon-rose hover:bg-pink-500/10 transition-all"
        >
          &rarr;
        </button>
      </div>
    </div>
  );
}
