import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import VoiceRecorder from './components/VoiceRecorder';
import AnalysisProgress from './components/AnalysisProgress';
import AnalysisSummary from './components/AnalysisSummary';
import VoiceAdvisoryBanner from './components/VoiceAdvisoryBanner';
import TranscriptPanel from './components/TranscriptPanel';
import ExtractionPanel from './components/ExtractionPanel';
import PolicyEvidence from './components/PolicyEvidence';
import CalculationPanel from './components/CalculationPanel';
import FindingsPanel from './components/FindingsPanel';

import { checkBackendHealth, getPolicyStatus, analyzeAudioClaim } from './services/api';
import { AlertCircle, Shield, Sparkles, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [policyStatus, setPolicyStatus] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResponse, setAnalysisResponse] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch initial backend and vectorstore status
  useEffect(() => {
    async function loadStatus() {
      const health = await checkBackendHealth();
      setBackendStatus(health);

      if (health.status === 'ok') {
        try {
          const policy = await getPolicyStatus();
          setPolicyStatus(policy);
        } catch (err) {
          console.warn('Could not fetch policy status:', err);
        }
      }
    }

    loadStatus();
    const interval = setInterval(loadStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  // Handle Audio Analysis Trigger
  const handleAnalyze = async (audioBlob, filename) => {
    setIsAnalyzing(true);
    setErrorMessage('');
    setAnalysisResponse(null);

    try {
      const result = await analyzeAudioClaim(audioBlob, filename);
      setAnalysisResponse(result);
    } catch (err) {
      console.error('Audio analysis error:', err);
      setErrorMessage(
        err.message || 'Analysis failed. Please ensure the backend is running and API keys are valid.'
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col font-sans selection:bg-teal-100 selection:text-teal-900">
      {/* SECTION A: Compact Professional Header */}
      <Header backendStatus={backendStatus} policyStatus={policyStatus} />

      {/* Main Content Workspace with Asymmetric Two-Column Balance */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* SECTION B: Page Introduction */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0F766E] bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200/80">
              Institutional Paper & Emerald Ledger
            </span>
            <span className="text-[11px] text-slate-300">•</span>
            <span className="text-[11px] text-slate-500 font-medium">
              Star Health Premier Policy Pre-Audit
            </span>
          </div>

          <h1 className="font-heading text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Understand Your Health Insurance Before Hospital Admission
          </h1>
          <p className="text-sm text-slate-600 mt-1.5 leading-relaxed max-w-3xl">
            Speak naturally in Hindi or Hinglish to understand policy conditions, room rent caps, potential deductions, and waiting periods before signing hospital admission consent.
          </p>

          <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-3.5 pt-3.5 border-t border-slate-100 text-xs text-slate-500">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#0F766E]"></span>
              <span>Gnani Prisma v2.5 STT</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-teal-600"></span>
              <span>Google Gemini 2.5 Flash</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-600"></span>
              <span>ChromaDB Vector Retrieval</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-indigo-600"></span>
              <span>Deterministic Rule Engine</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#115E59]"></span>
              <span>Gnani Timbre v2.5 TTS</span>
            </div>
          </div>
        </section>

        {/* SECTION C: Voice Claim Input Workspace */}
        <section>
          <VoiceRecorder onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
        </section>

        {/* Pipeline Progress Indicator */}
        {isAnalyzing && (
          <section>
            <AnalysisProgress isAnalyzing={isAnalyzing} />
          </section>
        )}

        {/* Error Notification */}
        {errorMessage && (
          <section className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-sm text-rose-800">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-heading font-bold text-rose-900 text-sm">Analysis Pipeline Failed</h4>
              <p className="text-xs text-rose-700 mt-0.5 leading-relaxed">{errorMessage}</p>
            </div>
          </section>
        )}

        {/* SECTION D: Main Results Workspace (Visible upon successful API response) */}
        {analysisResponse && (
          <div className="space-y-6">
            {/* 1. Executive Pre-Audit Summary */}
            <section>
              <AnalysisSummary analysisResponse={analysisResponse} />
            </section>

            {/* 2. Signature Dark-Teal Voice Advisory Dock */}
            <section>
              <VoiceAdvisoryBanner tts={analysisResponse.tts} />
            </section>

            {/* 3. Asymmetric Two-Column Split (Left ~38%, Right ~62%) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Speech Input Context & Parsed Entities (5 of 12 cols) */}
              <div className="lg:col-span-5 space-y-6">
                {/* Speech Transcription */}
                <TranscriptPanel
                  transcription={analysisResponse.transcription}
                  normalizedQuery={analysisResponse.extracted_information?.normalized_english_query}
                />

                {/* Extracted Insurance Parameters */}
                <ExtractionPanel info={analysisResponse.extracted_information} />
              </div>

              {/* Right Column: Findings, Math Receipt, Policy Evidence, Action Checklist (7 of 12 cols) */}
              <div className="lg:col-span-7 space-y-6">
                {/* Findings & Pre-Admission Patient Action Checklist */}
                <FindingsPanel
                  findings={analysisResponse.analysis?.findings}
                  warnings={analysisResponse.analysis?.warnings}
                  disclaimer={analysisResponse.analysis?.disclaimer}
                  checklist={analysisResponse.analysis?.checklist}
                />

                {/* Deterministic Financial Calculations Receipt */}
                <CalculationPanel
                  calculations={analysisResponse.analysis?.calculations}
                  excludedExpenses={analysisResponse.analysis?.excluded_expenses}
                  assumptions={analysisResponse.analysis?.assumptions}
                />

                {/* Retrieved Policy Evidence Accordion */}
                <PolicyEvidence clauses={analysisResponse.retrieved_clauses} />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Minimal Institutional Footer */}
      <footer className="border-t border-slate-200 bg-white py-5 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#0F766E]" />
            <span className="font-heading font-bold text-slate-800">BimaSakshi</span>
            <span className="text-slate-300">—</span>
            <span>AI Health Insurance Pre-Audit & Decision Support</span>
          </div>
          <div className="flex items-center gap-3 text-slate-500 text-[11px] font-mono">
            <span>Star Health Premier (SHAHLIP22226V012122)</span>
            <span>•</span>
            <span>Gnani AI + Google Gemini</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
