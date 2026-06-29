'use client';
import { useState, useEffect } from 'react';
import ChatInterface from '@/components/ChatInterface';
import LoveReasons from '@/components/LoveReasons';
import BirthdayCountdown from '@/components/BirthdayCountdown';
import ProposalModal from '@/components/ProposalModal';
import FloatingHearts from '@/components/FloatingHearts';

function useConfetti() {
  const fire = async () => {
    if (typeof window === 'undefined') return;
    const confetti = (await import('canvas-confetti')).default;

    const duration = 4000;
    const end = Date.now() + duration;

    const heartShape = confetti.shapeFromPath({
      path: 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z',
    });

    const colors = ['#ff2d8a', '#ff6b9d', '#ff9ec5', '#a855f7', '#ec4899'];

    (function frame() {
      confetti({
        particleCount: 5,
        angle: 60,
        spread: 70,
        origin: { x: 0, y: 0.7 },
        colors,
        shapes: [heartShape, 'circle'],
        scalar: 1.2,
      });
      confetti({
        particleCount: 5,
        angle: 120,
        spread: 70,
        origin: { x: 1, y: 0.7 },
        colors,
        shapes: [heartShape, 'circle'],
        scalar: 1.2,
      });

      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    })();
  };

  return fire;
}

export default function Home() {
  const [showProposal, setShowProposal] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [showBirthdayMessage, setShowBirthdayMessage] = useState(false);
  const fireConfetti = useConfetti();

  const handleCelebrate = () => {
    setShowBirthdayMessage(true);
    fireConfetti();
    setTimeout(() => setShowBirthdayMessage(false), 5000);
  };

  const handleProposalYes = () => {
    fireConfetti();
  };

  return (
    <main className="min-h-screen relative">
      <FloatingHearts />

      {/* Header */}
      <header className="relative z-10 pt-8 pb-4 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1
            className="text-4xl md:text-5xl font-bold text-white neon-text"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            SenaBot
          </h1>
          <p className="text-neon-rose mt-2 text-sm md:text-base opacity-80">
            Sena&apos;s Digi-Love Companion &mdash; because you deserve infinity, and this is my start.
          </p>
        </div>
      </header>

      {/* Navigation */}
      <nav className="relative z-10 max-w-4xl mx-auto px-4 mb-6">
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {[
            { id: 'chat', label: 'Digi Chat 💬', icon: '' },
            { id: 'love', label: 'Love Reasons 💝', icon: '' },
            { id: 'birthday', label: 'Birthday 🎂', icon: '' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'btn-love text-white shadow-lg shadow-pink-500/20'
                  : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent hover:border-pink-500/20'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10 max-w-4xl mx-auto px-4 pb-8">
        <div className="animate-fade-in">
          {activeTab === 'chat' && <ChatInterface />}
          {activeTab === 'love' && <LoveReasons />}
          {activeTab === 'birthday' && <BirthdayCountdown onCelebrate={handleCelebrate} />}
        </div>

        {/* The Future Button */}
        <div className="mt-8 text-center">
          <button
            onClick={() => setShowProposal(true)}
            className="group relative inline-flex items-center gap-2 px-6 py-3 rounded-2xl border border-pink-500/30 text-neon-rose hover:border-pink-500/60 hover:bg-pink-500/5 transition-all duration-300"
          >
            <span className="text-lg group-hover:animate-heart-beat">💍</span>
            <span className="text-sm font-medium">The Future</span>
            <span className="text-lg group-hover:animate-heart-beat">✨</span>
          </button>
        </div>
      </div>

      {/* Birthday Celebration Overlay */}
      {showBirthdayMessage && (
        <div className="fixed inset-0 z-40 flex items-center justify-center pointer-events-none">
          <div className="glass-card rounded-3xl p-8 text-center animate-slide-up max-w-md mx-4">
            <div className="text-5xl mb-4">🎂🎉👑</div>
            <h2
              className="text-3xl font-bold text-white neon-text mb-3"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Happy 20th Birthday, Sena!
            </h2>
            <p className="text-gray-300 leading-relaxed">
              20 years of you blessing this planet &mdash; and I&apos;m the lucky one
              who gets to love you through every single one to come. My beautiful,
              brilliant, breathtaking girl. Welcome to your 20s, queen. I love you
              more than words could ever capture. 💕
            </p>
            <img
              src="https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif"
              alt="birthday kiss"
              className="w-48 h-auto mx-auto mt-4 rounded-xl opacity-90"
            />
          </div>
        </div>
      )}

      {/* Proposal Modal */}
      <ProposalModal
        isOpen={showProposal}
        onClose={() => setShowProposal(false)}
        onYes={handleProposalYes}
      />

      {/* Footer */}
      <footer className="relative z-10 text-center py-6 text-xs text-gray-600">
        Made with infinite love by Digi, for Sena &mdash; forever and always 💕
      </footer>
    </main>
  );
}
