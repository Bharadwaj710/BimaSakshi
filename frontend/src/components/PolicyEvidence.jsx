import React, { useState } from 'react';
import { Database, ExternalLink, ChevronDown, ChevronUp, FileText, CheckCircle2 } from 'lucide-react';

export default function PolicyEvidence({ clauses }) {
  const [expandedClauses, setExpandedClauses] = useState({});

  if (!clauses || clauses.length === 0) return null;

  const toggleExpand = (id) => {
    setExpandedClauses((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-600" />
          <h3 className="text-base font-semibold text-slate-900">Retrieved Policy Evidence</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
            {clauses.length} Clauses Retrieved
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Authentic policy clauses retrieved via ChromaDB semantic vector search from official Star Health Premier policy wording.
      </p>

      {/* Clauses List */}
      <div className="space-y-3 mt-3.5">
        {clauses.map((clause, idx) => {
          const isExpanded = !!expandedClauses[clause.clause_id || idx];
          const fullText = clause.retrieved_text || '';
          const isLong = fullText.length > 200;

          return (
            <div
              key={clause.clause_id || idx}
              className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 hover:border-slate-300 transition-colors"
            >
              {/* Clause Header & Meta */}
              <div className="flex items-start justify-between gap-2 mb-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    {clause.clause_id}
                  </span>
                  <h4 className="text-xs font-semibold text-slate-900">
                    {clause.clause_title}
                  </h4>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white text-slate-600 border border-slate-200">
                    {clause.source_page}
                  </span>
                  {clause.distance !== undefined && (
                    <span className="text-[11px] font-mono text-slate-400">
                      dist: {Number(clause.distance).toFixed(3)}
                    </span>
                  )}
                </div>
              </div>

              {/* Text Excerpt / Full View */}
              <div className="p-3 rounded-md bg-white border border-slate-200 text-xs text-slate-700 leading-relaxed font-mono">
                {isExpanded || !isLong ? fullText : `${fullText.slice(0, 200)}...`}
              </div>

              {/* Bottom Row: Accordion Toggle + Official PDF Link */}
              <div className="mt-2.5 flex items-center justify-between text-xs flex-wrap gap-2">
                {isLong ? (
                  <button
                    type="button"
                    onClick={() => toggleExpand(clause.clause_id || idx)}
                    className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 text-[11px] cursor-pointer"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp className="w-3.5 h-3.5" /> Collapse Clause Text
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3.5 h-3.5" /> View Full Clause Wording
                      </>
                    )}
                  </button>
                ) : (
                  <span />
                )}

                {clause.policy_info?.pdf_url && (
                  <a
                    href={clause.policy_info.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-500 hover:text-blue-600 flex items-center gap-1 hover:underline text-[11px] ml-auto"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Official Policy PDF (Page {clause.source_page?.replace(/[^0-9]/g, '') || 'Doc'})
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
