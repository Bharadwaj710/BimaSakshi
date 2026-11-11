import React from 'react';
import { Calculator, AlertTriangle, ShieldCheck, HelpCircle, Receipt } from 'lucide-react';

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
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs">
      {/* Receipt Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-teal-50 text-[#0F766E] flex items-center justify-center">
            <Receipt className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-heading text-base font-bold text-slate-900 tracking-tight">
              Deterministic Financial Calculations
            </h3>
            <p className="text-xs text-slate-500">
              Itemized policy limits, room rent caps, and proportionate deductions
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
          Pure Python Rule Engine
        </span>
      </div>

      <p className="text-xs text-slate-500 mt-2.5">
        Evaluated strictly against Star Health Premier clauses and IRDAI guidelines without LLM mathematical hallucination.
      </p>

      {/* Itemized Calculation Receipts */}
      <div className="space-y-3.5 mt-4">
        {calculations.map((calc, idx) => {
          const isIllustrative = !!calc.illustrative_only;

          return (
            <div
              key={idx}
              className={`rounded-xl border transition-colors overflow-hidden ${
                isIllustrative
                  ? 'bg-amber-50/30 border-amber-300/80'
                  : 'bg-slate-50/70 border-slate-200'
              }`}
            >
              {/* Receipt Subheader */}
              <div className="p-4 pb-3 flex items-start justify-between gap-3 flex-wrap border-b border-slate-200/80 bg-white/70">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                    {calc.type.replace(/_/g, ' ')}
                  </h4>
                  <span className="text-xs font-mono text-slate-500 block mt-0.5">
                    Formula: {calc.formula}
                  </span>
                </div>

                {isIllustrative ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-100 text-amber-900 border border-amber-300">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                    Illustrative Calculation (₹10L Baseline)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Confirmed Policy Entitlement
                  </span>
                )}
              </div>

              {/* Illustrative Warning Banner */}
              {isIllustrative && (
                <div className="px-4 py-2 bg-amber-100/60 border-b border-amber-200 text-xs text-amber-900 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                  <span>
                    <strong>Illustrative only:</strong> Stated using a demonstration ₹10,00,000 Sum Insured baseline. Your actual sum insured was not specified in the recording.
                  </span>
                </div>
              )}

              {/* Calculated Result Box */}
              <div className="p-4 space-y-3">
                <div className="p-3.5 rounded-lg bg-white border border-slate-200 flex items-center justify-between flex-wrap gap-2 shadow-2xs">
                  <span className="text-xs font-medium text-slate-600">Calculated Limit / Entitlement:</span>
                  <span className="text-base font-mono font-bold text-slate-900 tabular-nums">
                    {calc.result !== null ? formatINR(calc.result) : 'Requires confirmation'}
                  </span>
                </div>

                {/* Plain-Language Explanation */}
                <p className="text-xs text-slate-700 leading-relaxed font-normal">
                  {calc.explanation}
                </p>

                {/* Input Parameters Receipt Table */}
                {calc.inputs && Object.keys(calc.inputs).length > 0 && (
                  <div className="pt-2.5 border-t border-slate-200/80">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1.5">
                      Input Values Evaluated:
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                      {Object.entries(calc.inputs).map(([k, v]) => (
                        <div key={k} className="p-2 rounded bg-white border border-slate-200/80 flex items-center justify-between">
                          <span className="text-slate-500 font-mono text-[11px] truncate">{k}:</span>
                          <span className="font-mono font-semibold text-slate-900 ml-2 tabular-nums">
                            {typeof v === 'number' ? formatINR(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Non-Associated / Exempt Items Notice */}
      {excludedExpenses && excludedExpenses.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <div className="flex items-center gap-1.5 mb-2">
            <ShieldCheck className="w-4 h-4 text-[#0F766E]" />
            <span className="text-xs font-semibold text-slate-800">
              Expenses Strictly Exempt from Proportionate Deductions (Per IRDAI & Policy Terms):
            </span>
          </div>
          <ul className="space-y-1 text-xs text-slate-600">
            {excludedExpenses.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[#0F766E] mt-1.5 shrink-0"></span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
