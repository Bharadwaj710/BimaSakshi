import React from 'react';
import { Loader2, Mic, BrainCircuit, Database, Calculator, Volume2, Shield } from 'lucide-react';

const PIPELINE_STEPS = [
  { id: 1, name: 'Speech Recognition', tech: 'Gnani Prisma v2.5', icon: Mic },
  { id: 2, name: 'Intent & Entity Extraction', tech: 'Gemini 2.5 Flash', icon: BrainCircuit },
  { id: 3, name: 'Policy Clause Retrieval', tech: 'ChromaDB MiniLM-L6', icon: Database },
  { id: 4, name: 'Deterministic Adjudication', tech: 'Rule Engine (1% Cap, Code Excl 02)', icon: Calculator },
  { id: 5, name: 'Vernacular Audio Synthesis', tech: 'Gnani Timbre v2.5 (Nalini)', icon: Volume2 },
];

export default function AnalysisProgress({ isAnalyzing }) {
  if (!isAnalyzing) return null;

  return (
    <div className="bg-white border border-teal-200/90 rounded-xl p-5 sm:p-6 shadow-xs">
      {/* Header with Honest Loading State */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-teal-50 text-[#0F766E] border border-teal-200/60 flex items-center justify-center shrink-0">
            <Loader2 className="w-5 h-5 animate-spin text-[#0F766E]" />
          </div>
          <div>
            <h3 className="font-heading text-base font-semibold text-slate-900 flex items-center gap-2">
              Analyzing Health Insurance Policy Claim
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Evaluating speech audio against official Star Health Premier terms. This typically takes 5–15 seconds.
            </p>
          </div>
        </div>

        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-50 text-[#0F766E] border border-teal-200">
          <span className="h-1.5 w-1.5 rounded-full bg-[#0F766E] animate-pulse"></span>
          Pipeline Active
        </span>
      </div>

      {/* Pipeline Architecture Cards */}
      <div className="mt-4">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-2.5">
          Atomic Pipeline Operations in Execution:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {PIPELINE_STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.id}
                className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="h-7 w-7 rounded-md bg-white border border-slate-200 text-[#0F766E] flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-mono font-medium text-slate-400">
                    Step {step.id}
                  </span>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-900 leading-snug">
                    {step.name}
                  </h4>
                  <p className="text-[11px] text-slate-500 font-mono mt-0.5 line-clamp-1">
                    {step.tech}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Honest Indeterminate Progress Line */}
      <div className="mt-4 pt-3.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-[#0F766E]" />
          Zero LLM hallucination: all financial limits and deductions are computed deterministically.
        </span>
        <span className="font-mono text-[11px] text-slate-400 hidden sm:inline">
          FastAPI POST /api/analyze-audio
        </span>
      </div>
    </div>
  );
}
