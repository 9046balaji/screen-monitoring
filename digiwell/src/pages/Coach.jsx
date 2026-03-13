import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { chatWithLifeCoach } from '../api/digiwell';

export default function Coach() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: "Hi! I'm your local DigiWell coach. I securely analyze your on-device screen time to give you personalized wellness advice. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endOfMessagesRef = useRef(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const { response } = await chatWithLifeCoach(userMessage);
      setMessages(prev => [...prev, { role: 'assistant', text: response }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: "Sorry, I ran into an issue connecting to the AI. Ensure the Flask server is running." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg mr-4">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-800">DigiWell AI Coach</h2>
          <p className="text-sm text-slate-600 dark:text-slate-500">100% Local • Privacy-First • Context-Aware</p>
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
                msg.role === 'user' ? 'bg-blue-600 text-white ml-4' : 'bg-indigo-600 text-white mr-4'
              }`}>
                {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              <div className={`px-5 py-3 rounded-2xl ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-none' 
                  : 'bg-white text-slate-800 border border-slate-200 shadow-sm rounded-tl-none'
              }`}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex flex-row max-w-[80%]">
              <div className="flex-shrink-0 h-10 w-10 rounded-full bg-indigo-600 text-white mr-4 flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
              <div className="px-5 py-3 rounded-2xl bg-white border border-slate-200 shadow-sm rounded-tl-none flex items-center gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={handleSubmit} className="flex gap-2 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your screen time, wellness risk, or strategies..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 text-slate-800 bg-white rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:bg-slate-50 disabled:text-slate-600 dark:text-slate-400"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-5 flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:bg-slate-300 shadow-sm"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}