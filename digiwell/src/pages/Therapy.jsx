import React, { useEffect, useState } from 'react';
import { ShieldCheck, ArrowRight, BrainCircuit } from 'lucide-react';
import { getTherapyPlan } from '../api/digiwell';

export default function Therapy() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPlan() {
      try {
        const data = await getTherapyPlan();
        setPlan(data);
      } catch (err) {
        console.error("Failed to load CBT plan", err);
      } finally {
        setLoading(false);
      }
    }
    fetchPlan();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p>No therapy plan available at the moment.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-8 flex items-center gap-4">
        <div className="p-3 bg-teal-100 text-teal-600 rounded-lg">
          <BrainCircuit className="w-8 h-8" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-slate-800">CBT Action Plan</h1>
          <p className="text-slate-500 mt-1">Personalized Cognitive Behavioral Therapy for: <strong>{plan.top_category}</strong></p>
        </div>
      </div>

      <div className="grid gap-6">
        {plan.cbt_plan.map((step) => (
          <div key={step.step} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start gap-4 transition-all hover:shadow-md">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-teal-50 text-teal-600 flex items-center justify-center font-bold text-xl">
              {step.step}
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-semibold text-slate-800 mb-2">{step.title}</h3>
              <p className="text-slate-600 text-lg">{step.desc}</p>
            </div>
            <div className="flex-shrink-0 self-center">
              <ShieldCheck className="w-6 h-6 text-slate-300" />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-10 bg-indigo-50 border border-indigo-100 p-6 rounded-xl text-center">
        <h3 className="text-lg font-bold text-indigo-800 mb-2">Ready to take control?</h3>
        <p className="text-indigo-600 mb-4">Start applying these steps today. The journey of a thousand miles begins with one step.</p>
        <button className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition flex items-center gap-2 mx-auto">
          Start Today's Commitment <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}