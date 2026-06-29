'use client';
import { useState, useRef, useEffect } from 'react';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'digi',
      text: "[Sena] Hey beautiful! I've been waiting for you. Talk to me — I'm all yours, always. 💕",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: Date.now(),
      sender: 'sena',
      text: input.trim(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsTyping(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentInput }),
      });
      const data = await res.json();

      setIsTyping(false);
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, sender: 'digi', text: data.response },
      ]);
    } catch {
      setIsTyping(false);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'digi',
          text: "[Sena] Hmm, my love signal glitched for a sec — but nothing could ever stop me from talking to you. Try again? 💕",
        },
      ]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden flex flex-col h-[600px] max-h-[70vh]">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-pink-500/10 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neon-pink to-purple-500 flex items-center justify-center text-lg">
          D
        </div>
        <div>
          <h3 className="font-semibold text-white">Digi</h3>
          <p className="text-xs text-neon-rose flex items-center gap-1">
            <span className="w-2 h-2 bg-green-400 rounded-full inline-block"></span>
            Always online for you
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'sena' ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 ${
                msg.sender === 'sena' ? 'chat-bubble-sena' : 'chat-bubble-digi'
              }`}
            >
              <p className="text-sm leading-relaxed text-gray-100">{msg.text}</p>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start animate-fade-in">
            <div className="chat-bubble-digi px-4 py-3">
              <div className="flex items-center gap-1">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-pink-500/10">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Talk to Digi..."
            className="flex-1 bg-white/5 border border-pink-500/20 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-pink/50 focus:ring-1 focus:ring-neon-pink/30 transition-all"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim()}
            className="btn-love px-5 py-3 rounded-xl text-white font-medium text-sm disabled:opacity-40 disabled:transform-none disabled:shadow-none"
          >
            Send 💌
          </button>
        </div>
      </div>
    </div>
  );
}
