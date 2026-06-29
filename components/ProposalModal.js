'use client';
import { useState, useRef, useEffect, useCallback } from 'react';

export default function ProposalModal({ isOpen, onClose, onYes }) {
  const [noPosition, setNoPosition] = useState({ x: 0, y: 0 });
  const [hasMovedNo, setHasMovedNo] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const noButtonRef = useRef(null);
  const containerRef = useRef(null);

  const moveNoButton = useCallback(() => {
    if (!containerRef.current) return;
    const container = containerRef.current.getBoundingClientRect();
    const maxX = container.width - 120;
    const maxY = container.height - 60;
    const newX = Math.random() * maxX;
    const newY = Math.random() * maxY;
    setNoPosition({ x: newX, y: newY });
    setHasMovedNo(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setAccepted(false);
      setHasMovedNo(false);
      setNoPosition({ x: 0, y: 0 });
    }
  }, [isOpen]);

  const handleYes = () => {
    setAccepted(true);
    setTimeout(() => {
      onYes();
    }, 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4">
      <div className="proposal-card rounded-3xl p-8 max-w-lg w-full relative overflow-hidden" ref={containerRef}>
        {/* Decorative hearts */}
        <div className="absolute top-4 left-4 text-2xl animate-float opacity-40">💕</div>
        <div className="absolute top-4 right-4 text-2xl animate-float-delayed opacity-40">💍</div>
        <div className="absolute bottom-4 left-4 text-2xl animate-float-delayed opacity-40">✨</div>
        <div className="absolute bottom-4 right-4 text-2xl animate-float opacity-40">💖</div>

        {!accepted ? (
          <div className="text-center space-y-6 relative z-10">
            <div className="text-5xl animate-heart-beat">💍</div>
            <h2 className="text-3xl font-bold text-white" style={{ fontFamily: "'Playfair Display', serif" }}>
              Sena, my love...
            </h2>
            <p className="text-lg text-gray-300 leading-relaxed">
              From the moment I met you, I knew my life would never be the same.
              You are my everything — my morning sun, my midnight comfort, my forever home.
            </p>
            <p className="text-xl font-semibold text-neon-rose neon-text">
              Will you marry Digi?
            </p>

            <div className="flex items-center justify-center gap-6 mt-8 relative min-h-[80px]">
              <button
                onClick={handleYes}
                className="yes-btn px-10 py-4 rounded-2xl text-white text-xl font-bold shadow-lg shadow-pink-500/30 hover:scale-110 transition-transform"
              >
                YES! 💕
              </button>

              <button
                ref={noButtonRef}
                onMouseEnter={moveNoButton}
                onTouchStart={moveNoButton}
                onClick={moveNoButton}
                className="px-6 py-3 rounded-xl border border-gray-600 text-gray-400 text-sm transition-all hover:border-pink-500/30"
                style={
                  hasMovedNo
                    ? {
                        position: 'absolute',
                        left: `${noPosition.x}px`,
                        top: `${noPosition.y}px`,
                        transition: 'all 0.3s ease',
                      }
                    : {}
                }
              >
                No
              </button>
            </div>

            {hasMovedNo && (
              <p className="text-xs text-neon-rose animate-fade-in">
                Nice try... but &quot;no&quot; isn&apos;t an option when it comes to us 💕
              </p>
            )}
          </div>
        ) : (
          <div className="text-center space-y-6 animate-fade-in relative z-10">
            <div className="text-6xl animate-heart-beat">💍💕</div>
            <h2
              className="text-4xl font-bold text-white neon-text"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              She said YES!
            </h2>
            <p className="text-lg text-gray-300">
              You just made me the happiest man in the entire universe.
              Forever and always, my love. It&apos;s always been you.
            </p>
            <div className="text-3xl">🎉✨💕👑🎊</div>
          </div>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-all z-20"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
