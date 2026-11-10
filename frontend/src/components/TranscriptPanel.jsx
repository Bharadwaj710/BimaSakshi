import React, { useState } from 'react';
import { FileText, Clock, Hash, Globe, ChevronDown, ChevronUp } from 'lucide-react';

export default function TranscriptPanel({ transcription, normalizedQuery }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!transcription) return null;

  const isLong = (transcription.text || '').length > 220;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <h3 className="text-base font-semibold text-slate-900">Speech Transcription</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
            {transcription.model || 'prisma-v2.5'}
          </span>
        </div>
      </div>

      {/* Raw Hindi Transcript */}
      <div className="mt-3.5">
        <span className="text-xs font-medium text-slate-500 block mb-1.5">
          Prisma v2.5 Output (Raw Hindi Audio Transcription):
        </span>
        <div
          className={`p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-800 font-devanagari text-sm sm:text-base leading-relaxed break-words transition-all ${
            !isExpanded && isLong ? 'max-h-24 overflow-hidden relative' : ''
          }`}
        >
          "{transcription.text}"
          {!isExpanded && isLong && (
            <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-slate-50 to-transparent pointer-events-none" />
          )}
        </div>

        {isLong && (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" /> Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" /> Show full transcript
              </>
            )}
          </button>
        )}
      </div>

      {/* Latency & Metadata */}
      <div className="mt-3 flex items-center justify-between flex-wrap gap-2 text-xs text-slate-500">
        <div className="flex items-center gap-3">
          {transcription.latency_sec !== null && transcription.latency_sec !== undefined && (
            <span className="flex items-center gap-1 font-mono text-emerald-700">
              <Clock className="w-3.5 h-3.5" />
              {Number(transcription.latency_sec).toFixed(2)}s STT latency
            </span>
          )}
          {transcription.request_id && (
            <span className="flex items-center gap-1 font-mono text-slate-400 text-[11px]">
              <Hash className="w-3 h-3" />
              ID: {transcription.request_id.slice(0, 16)}...
            </span>
          )}
        </div>
      </div>

      {/* Normalized English Semantic Query (Gemini) */}
      {normalizedQuery && (
        <div className="mt-4 pt-3.5 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 mb-1.5">
            <Globe className="w-3.5 h-3.5 text-blue-600" />
            <span>ChromaDB Normalized English Query (Gemini 2.5 Flash):</span>
          </div>
          <div className="p-2.5 rounded-md bg-blue-50/50 border border-blue-200/80 text-xs font-mono text-blue-900 leading-relaxed break-words">
            {normalizedQuery}
          </div>
        </div>
      )}
    </div>
  );
}
