import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert, FileText, Activity, HelpCircle, Shield } from 'lucide-react';

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
  let statusTitle = 'Pre-Audit Assessment Completed';
  let statusBadge = 'Entitlements Verified';
  let badgeStyle = 'bg-emerald-50 text-emerald-800 border-emerald-300';
  let cardBorder = 'border-slate-200';

  if (hasWarnings || hasMissing) {
    statusTitle = 'Pre-Admission Verification Required';
    statusBadge = hasWarnings ? 'Action Required Before Admission' : 'Policy Confirmation Needed';
    badgeStyle = 'bg-amber-50 text-amber-900 border-amber-300';
    cardBorder = 'border-amber-300/80';
  }

  return (
    <div className={`bg-white border ${cardBorder} rounded-xl p-5 sm:p-6 shadow-xs`}>
      {/* Executive Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-lg font-bold text-slate-900 tracking-tight">
              {statusTitle}
            </h2>
            <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${badgeStyle}`}>
              {statusBadge}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Informational policy pre-audit evaluated against Star Health Premier (SHAHLIP22226V012122).
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-700 font-medium">
            {clauses.length} Clauses Matched
          </span>
        </div>
      </div>

      {/* 3 Key Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
        {/* Metric 1 */}
        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium uppercase tracking-wider">
            Stated Condition / Procedure
          </span>
          <span className="text-sm font-bold text-slate-900 mt-1 block truncate">
            {info.diagnosis_or_condition || info.treatment_type || 'Unspecified Condition'}
          </span>
        </div>

        {/* Metric 2 */}
        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium uppercase tracking-wider">
            Sum Insured Entitlement
          </span>
          <span className="text-sm font-bold text-slate-900 mt-1 block font-mono tabular-nums">
            {info.sum_insured
              ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(info.sum_insured)
              : 'Unconfirmed (₹10L Baseline)'}
          </span>
        </div>

        {/* Metric 3 */}
        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-slate-500 text-[11px] block font-medium uppercase tracking-wider">
            Pre-Audit Finding
          </span>
          <span className="text-sm font-bold text-slate-900 mt-1 block">
            {hasWarnings
              ? `${warnings.length} policy caveat${warnings.length > 1 ? 's' : ''} flagged`
              : hasMissing
              ? 'Schedule confirmation required'
              : 'No major deductions identified'}
          </span>
        </div>
      </div>
    </div>
  );
}
