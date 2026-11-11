import React from 'react';
import { Shield, FileText, CheckCircle2, AlertCircle, Cpu } from 'lucide-react';

export default function Header({ backendStatus, policyStatus }) {
  const isConnected = backendStatus?.status === 'ok' && backendStatus?.vector_store_initialized;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Descriptor */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-[#0F766E] text-white flex items-center justify-center shadow-xs">
              <Shield className="w-5 h-5 text-teal-100" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-heading font-bold text-slate-900 text-lg tracking-tight">BimaSakshi</span>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-teal-50 text-[#0F766E] border border-teal-200/80">
                  Pre-Audit
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Vernacular Health Insurance Decision Support
              </p>
            </div>
          </div>

          {/* Right Status Group */}
          <div className="flex items-center gap-2.5 sm:gap-3 text-xs">
            {/* Active Policy Context */}
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-slate-700">
              <FileText className="w-3.5 h-3.5 text-[#0F766E]" />
              <span className="font-medium text-slate-800">Star Health Premier</span>
              <span className="text-slate-400 font-mono text-[11px]">SHAHLIP22226V012122</span>
            </div>

            {/* Backend Connectivity Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200">
              {isConnected ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-emerald-600"></span>
                  <span className="text-slate-700 font-medium">System Ready</span>
                  {policyStatus?.indexed_documents_count && (
                    <span className="hidden lg:inline text-slate-400 font-mono text-[11px]">
                      ({policyStatus.indexed_documents_count} clauses)
                    </span>
                  )}
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
                  <span className="text-amber-700 font-medium">Connecting...</span>
                </>
              )}
            </div>

            {/* AI Stack Attribution */}
            <div className="hidden lg:flex items-center gap-1.5 text-slate-500 text-[11px]">
              <Cpu className="w-3.5 h-3.5 text-slate-400" />
              <span>Gnani AI + Gemini</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
