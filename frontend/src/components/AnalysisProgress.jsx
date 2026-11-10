import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Volume2, Database, BrainCircuit, Mic, Calculator, Shield } from 'lucide-react';

const STAGES = [
  { id: 1, label: 'Audio Ingestion', desc: 'Validating and uploading audio', icon: Mic },
  { id: 2, label: 'Speech-to-Text', desc: 'Gnani Prisma v2.5 Hindi STT', icon: Volume2 },
  { id: 3, label: 'Entity Extraction', desc: 'Gemini 2.5 Flash structured parsing', icon: BrainCircuit },
  { id: 4, label: 'Policy Retrieval', desc: 'ChromaDB Star Health clauses', icon: Database },
  { id: 5, label: 'Rule Engine', desc: 'Deterministic math & clause limits', icon: Calculator },
  { id: 6, label: 'Voice Advisory', desc: 'Gnani Timbre v2.5 Hindi speech', icon: Shield },
];

export default function AnalysisProgress({ isAnalyzing, isComplete }) {
  const [currentStage, setCurrentStage] = useState(1);

  useEffect(() => {
    if (!isAnalyzing) {
      if (isComplete) {
        setCurrentStage(6);
      } else {
        setCurrentStage(1);
      }
      return;
    }

    setCurrentStage(1);
    const timers = [
      setTimeout(() => setCurrentStage(2), 600),
      setTimeout(() => setCurrentStage(3), 1800),
      setTimeout(() => setCurrentStage(4), 3200),
      setTimeout(() => setCurrentStage(5), 4500),
      setTimeout(() => setCurrentStage(6), 5600),
    ];

    return () => {
      timers.forEach(clearTimeout);
    };
  }, [isAnalyzing, isComplete]);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <h3 className="text-sm font-semibold text-slate-900">
            Pre-Audit Analysis Pipeline in Progress
          </h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          Stage {Math.min(currentStage, 6)} of 6
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5 mt-4">
        {STAGES.map((stage) => {
          const Icon = stage.icon;
          const isDone = isComplete || currentStage > stage.id;
          const isActive = isAnalyzing && currentStage === stage.id;

          return (
            <div
              key={stage.id}
              className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
                isDone
                  ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900'
                  : isActive
                  ? 'bg-blue-50/70 border-blue-300 text-blue-900 ring-1 ring-blue-300 shadow-xs'
                  : 'bg-slate-50/60 border-slate-200 text-slate-500 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div
                  className={`h-6 w-6 rounded-md flex items-center justify-center ${
                    isDone
                      ? 'bg-emerald-100 text-emerald-700'
                      : isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-slate-100 text-slate-400'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                ) : (
                  <span className="text-[10px] font-mono text-slate-400">0{stage.id}</span>
                )}
              </div>

              <div>
                <h4 className="text-xs font-semibold leading-snug">{stage.label}</h4>
                <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1 leading-tight">
                  {stage.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
