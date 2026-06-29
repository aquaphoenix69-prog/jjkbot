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
    const maxX = Math.max(container.width - 80, 50);
    const maxY = Math.max(container.height - 50, 50);
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
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-3 sm:p-4">
      <div className="proposal-card rounded-2xl sm:rounded-3xl p-5 sm:p-8 max-w-lg w-full relative overflow-hidden max-h-[90dvh] overflow-y-auto" ref={containerRef}>
        {/* Decorative hearts */}
        <div className="absolute top-3 left-3 text-xl sm:text-2xl animate-float opacity-40">💕</div>
        <div className="absolute top-3 right-10 text-xl sm:text-2xl animate-float-delayed opacity-40">💍</div>

        {!accepted ? (
          <div className="text-center space-y-4 sm:space-y-6 relative z-10">
            <div className="text-4xl sm:text-5xl animate-heart-beat">💍</div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white" style={{ fontFamily: "'Playfair Display', serif" }}>
              Sena, my love...
            </h2>
            <p className="text-sm sm:text-lg text-gray-300 leading-relaxed px-2">
              From the moment I met you, I knew my life would never be the same.
              You are my everything — my morning sun, my midnight comfort, my forever home.
            </p>
            <p className="text-lg sm:text-xl font-semibold text-neon-rose neon-text">
              Will you marry Digi?
            </p>

            <div className="flex items-center justify-center gap-4 sm:gap-6 mt-6 sm:mt-8 relative min-h-[70px] sm:min-h-[80px]">
              <button
                onClick={handleYes}
                className="yes-btn px-8 sm:px-10 py-3 sm:py-4 rounded-2xl text-white text-lg sm:text-xl font-bold shadow-lg shadow-pink-500/30 active:scale-95 hover:scale-110 transition-transform"
              >
                YES! 💕
              </button>

              <button
                ref={noButtonRef}
                onMouseEnter={moveNoButton}
                onTouchStart={moveNoButton}
                onClick={moveNoButton}
                className="px-4 sm:px-6 py-2 sm:py-3 rounded-xl border border-gray-600 text-gray-400 text-xs sm:text-sm transition-all"
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
              <p className="text-[11px] sm:text-xs text-neon-rose animate-fade-in">
                Nice try... but &quot;no&quot; isn&apos;t an option when it comes to us 💕
              </p>
            )}
          </div>
        ) : (
          <div className="text-center space-y-4 sm:space-y-6 animate-fade-in relative z-10">
            <div className="text-5xl sm:text-6xl animate-heart-beat">💍💕</div>
            <h2
              className="text-3xl sm:text-4xl font-bold text-white neon-text"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              She said YES!
            </h2>
            <p className="text-sm sm:text-lg text-gray-300 px-2">
              You just made me the happiest man in the entire universe.
              Forever and always, my love. It&apos;s always been you.
            </p>
            <div className="text-2xl sm:text-3xl">🎉✨💕👑🎊</div>
          </div>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-2 right-2 sm:top-3 sm:right-3 w-8 h-8 rounded-full flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-all z-20"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
