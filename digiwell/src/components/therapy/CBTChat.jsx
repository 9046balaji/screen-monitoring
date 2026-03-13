import React, { useState, useEffect } from 'react';
import { Send, User, Bot, AlertCircle } from 'lucide-react';
import { startTherapySession, respondTherapySession } from '../../api/digiwell';
import { useCommitment } from '../../hooks/useCommitment';
import toast from 'react-hot-toast';

export default function CBTChat({ onCommitmentRecommended }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        const res = await startTherapySession();
        setSessionId(res.session_id);
        setMessages(res.messages || []);
      } catch (e) {
        toast.error('Failed to start chat');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await respondTherapySession(sessionId, userMsg);
      setMessages(res.messages || [...messages, { role: 'user', content: userMsg }, { role: 'assistant', content: res.agent_reply }]);
      
      if (res.suggested_commitment && Object.keys(res.suggested_commitment).length > 0) {
        onCommitmentRecommended(res.suggested_commitment);
      }
    } catch (err) {
      toast.error('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden h-[500px]">
      <div className="bg-indigo-50 dark:bg-indigo-900/50 p-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
        <Bot className="text-indigo-600 dark:text-indigo-400" />
        <div>
          <h3 className="font-semibold text-slate-800 dark:text-slate-200">AI CBT Coach</h3>
          <p className="text-xs text-slate-500">Interactive Reflection</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${m.role === 'user' ? 'bg-slate-200 dark:bg-slate-700' : 'bg-indigo-100 text-indigo-600'}`}>
              {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`p-3 rounded-xl max-w-[75%] ${m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <Bot size={16} />
            </div>
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{animationDelay: '0.2s'}}></span>
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{animationDelay: '0.4s'}}></span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={sendMessage} className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Share what's on your mind..."
          className="flex-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-indigo-500 text-slate-900 dark:text-slate-100"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={!input.trim() || loading}
          className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
}
