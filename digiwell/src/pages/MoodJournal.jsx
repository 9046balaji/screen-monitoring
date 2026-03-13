import { useState, useEffect } from 'react';
import { BookOpen, Smile, Frown, PenTool, Flame } from 'lucide-react';
import { getMoodJournals, addMoodJournal } from '../api/digiwell';
import toast from 'react-hot-toast';

export default function MoodJournal() {
  const [journals, setJournals] = useState([]);
  const [entry, setEntry] = useState('');
  const [moodScore, setMoodScore] = useState(3);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJournals();
  }, []);

  const fetchJournals = async () => {
    try {
      const data = await getMoodJournals();
      setJournals(data.reverse()); // newest first
    } catch (err) {
      console.error(err);
      toast.error('Failed to load journals');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!entry.trim()) return;

    try {
      await addMoodJournal(entry, moodScore);
      toast.success('Journal entry saved!');
      setEntry('');
      setMoodScore(3);
      fetchJournals();
    } catch (err) {
      console.error(err);
      toast.error('Failed to save journal');
    }
  };

  return (
    <div className="space-y-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
          <BookOpen className="text-indigo-400" />
          Mood Journal
        </h1>
        <p className="text-slate-600 dark:text-slate-400 mt-2">Track how your screen time affects your mental wellbeing over time.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Input Form */}
        <div className="lg:col-span-1 border border-slate-300 dark:border-slate-700 bg-surface rounded-2xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <PenTool className="w-5 h-5 text-indigo-400" />
            New Entry
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-700 dark:text-slate-300 mb-2">How are you feeling?</label>
              <div className="flex justify-between items-center bg-base p-2 rounded-xl border border-slate-300 dark:border-slate-700">
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    type="button"
                    onClick={() => setMoodScore(score)}
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                      moodScore === score ? 'bg-indigo-600 text-white font-bold' : 'bg-surface text-slate-600 dark:text-slate-400 hover:bg-slate-300 dark:hover:bg-slate-700'
                    }`}
                  >
                    {score}
                  </button>
                ))}
              </div>
              <div className="flex justify-between text-xs text-slate-600 dark:text-slate-500 mt-1 px-1">
                <span>Awful</span>
                <span>Great</span>
              </div>
            </div>

            <div>
              <label className="block text-sm text-slate-700 dark:text-slate-300 mb-2">Reflect on your usage</label>
              <textarea
                value={entry}
                onChange={(e) => setEntry(e.target.value)}
                rows={4}
                className="w-full bg-base border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="I felt really anxious after spending 2 hours scrolling..."
              />
            </div>

            <button
              type="submit"
              disabled={!entry.trim()}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-semibold transition-colors disabled:opacity-50"
            >
              Save Entry
            </button>
          </form>
        </div>

        {/* History */}
        <div className="lg:col-span-2 border border-slate-300 dark:border-slate-700 bg-surface rounded-2xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <Flame className="w-5 h-5 text-orange-400" />
            Recent Logs
          </h2>
          
          {loading ? (
            <p className="text-slate-600 dark:text-slate-400">Loading journals...</p>
          ) : journals.length === 0 ? (
            <div className="text-center py-10 text-slate-600 dark:text-slate-500">
              <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>No entries yet. Start tracking your mood!</p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
              {journals.map((j, idx) => (
                <div key={idx} className="bg-base border border-slate-300 dark:border-slate-700 rounded-xl p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold pb-0.5 ${
                        j.polarity > 0.2 ? 'bg-success/20 text-success' : j.polarity < -0.2 ? 'bg-danger/20 text-danger' : 'bg-warning/20 text-warning'
                      }`}>
                        {j.polarity > 0.2 ? <Smile className="w-5 h-5"/> : j.polarity < -0.2 ? <Frown className="w-5 h-5"/> : '😐'}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          {new Date(j.date).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
                        </p>
                        <p className="text-xs text-slate-600 dark:text-slate-500">Sentiment: {j.polarity > 0.2 ? 'Positive' : j.polarity < -0.2 ? 'Negative' : 'Neutral'} ({j.polarity})</p>
                      </div>
                    </div>
                    <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 bg-slate-200 dark:bg-slate-800 px-2 py-1 rounded-md">
                      Score: {j.mood_score}/5
                    </div>
                  </div>
                  <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{j.entry}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}