import React from 'react';
import { Calculator, AlertTriangle, ShieldCheck, HelpCircle } from 'lucide-react';

export default function CalculationPanel({ calculations, excludedExpenses, assumptions }) {
  if (!calculations || calculations.length === 0) return null;

  // Format currency in Indian format
  const formatINR = (val) => {
    if (val === null || val === undefined) return 'Requires confirmation';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-blue-600" />
          <h3 className="text-base font-semibold text-slate-900">Deterministic Financial Calculations</h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
          Pure Python Rule Engine
        </span>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Mathematical rules evaluated without LLM hallucination, adhering strictly to Star Health Premier limits and IRDAI guidelines.
      </p>

      {/* Calculations List */}
      <div className="space-y-3 mt-3.5">
        {calculations.map((calc, idx) => {
          const isIllustrative = !!calc.illustrative_only;

          return (
            <div
              key={idx}
              className={`p-4 rounded-lg border transition-colors ${
                isIllustrative
                  ? 'bg-amber-50/40 border-amber-200'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              {/* Header & Badges */}
              <div className="flex items-start justify-between gap-2 mb-2 flex-wrap">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    {calc.type.replace(/_/g, ' ')}
                  </h4>
                  <span className="text-xs font-mono text-slate-500 block mt-0.5">
                    Formula: {calc.formula}
                  </span>
                </div>

                {isIllustrative ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                    Illustrative Only (Assumed ₹10 Lakh SI)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Confirmed Policy Entitlement
                  </span>
                )}
              </div>

              {/* Calculated Result */}
              <div className="my-2.5 p-3 rounded-md bg-white border border-slate-200 flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs font-medium text-slate-600">Calculated Limit / Entitlement:</span>
                <span className="text-sm font-mono font-bold text-slate-900">
                  {calc.result !== null ? formatINR(calc.result) : 'Requires user confirmation'}
                </span>
              </div>

              {/* Explanation Text */}
              <p className="text-xs text-slate-600 leading-relaxed">
                {calc.explanation}
              </p>

              {/* Inputs Breakdown */}
              {calc.inputs && Object.keys(calc.inputs).length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-200 flex items-center gap-4 flex-wrap text-[11px] text-slate-500">
                  <span className="font-medium text-slate-700">Inputs evaluated:</span>
                  {Object.entries(calc.inputs).map(([k, v]) => (
                    <span key={k} className="font-mono">
                      <span className="text-slate-400">{k}:</span>{' '}
                      <span className="text-slate-800 font-medium">
                        {typeof v === 'number' ? formatINR(v) : String(v)}
                      </span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Assumptions Applied */}
      {assumptions && assumptions.length > 0 && (
        <div className="mt-3.5 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
          <span className="font-semibold text-slate-700 block mb-1">Assumptions Applied in Pre-Audit:</span>
          <ul className="space-y-1">
            {assumptions.map((item, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-blue-600 mt-1">•</span>
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Non-Associated Expenses Exemption Reminder */}
      {excludedExpenses && excludedExpenses.length > 0 && (
        <div className="mt-3.5 p-3.5 rounded-lg bg-emerald-50/70 border border-emerald-200">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-900 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-700" />
            <span>IRDAI Mandatory Exemptions from Proportionate Deductions:</span>
          </div>
          <p className="text-[11px] text-emerald-800 leading-relaxed">
            The following non-associated medical expenses must not be proportionately reduced, even when room rent limits are exceeded:
          </p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {excludedExpenses.map((exp, idx) => (
              <span
                key={idx}
                className="text-[11px] px-2 py-0.5 rounded bg-white text-emerald-800 border border-emerald-200 font-medium"
              >
                {exp}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
