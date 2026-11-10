import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert, FileText, Activity, HelpCircle } from 'lucide-react';

export default function AnalysisSummary({ analysisResponse }) {
  if (!analysisResponse) return null;

  const info = analysisResponse.extracted_information || {};
  const analysis = analysisResponse.analysis || {};
  const warnings = analysis.warnings || [];
  const missingInfo = info.missing_information || [];
  const clauses = analysisResponse.retrieved_clauses || [];

  const hasWarnings = warnings.length > 0;
  const hasMissing = missingInfo.length > 0;

  // Determine overall status
  let statusTitle = 'Pre-Audit Analysis Completed';
  let statusBadge = 'Analysis Complete';
  let badgeStyle = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  let cardBorder = 'border-slate-200';

  if (hasWarnings || hasMissing) {
    statusTitle = 'Pre-Admission Verification Required';
    statusBadge = hasWarnings ? 'Action Required' : 'Information Missing';
    badgeStyle = 'bg-amber-50 text-amber-800 border-amber-200';
    cardBorder = 'border-amber-200/80';
  }

  return (
    <div className={`bg-white border ${cardBorder} rounded-xl p-5 shadow-sm`}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3.5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900">{statusTitle}</h3>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badgeStyle}`}>
              {statusBadge}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Vernacular audio processed with Gnani AI, Google Gemini 2.5 Flash, and ChromaDB.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200">
            {clauses.length} Clauses Matched
          </span>
        </div>
      </div>

      {/* 3 Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mt-3.5">
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium">Stated Condition / Procedure</span>
          <span className="text-xs font-semibold text-slate-900 mt-0.5 block truncate">
            {info.diagnosis_or_condition || info.treatment_type || 'Unspecified Condition'}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium">Policy Sum Insured</span>
          <span className="text-xs font-semibold text-slate-900 mt-0.5 block">
            {info.sum_insured
              ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(info.sum_insured)
              : 'Unconfirmed (₹10L Illustrative Baseline)'}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium">Audit Verification Result</span>
          <span className="text-xs font-semibold text-slate-900 mt-0.5 block">
            {hasWarnings
              ? `${warnings.length} policy discrepancy found`
              : hasMissing
              ? 'Schedule confirmation required'
              : 'No major discrepancies identified'}
          </span>
        </div>
      </div>
    </div>
  );
}

