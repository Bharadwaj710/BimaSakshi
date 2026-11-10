import React from 'react';
import { AlertCircle, CheckSquare, ShieldAlert, Info, Check } from 'lucide-react';

export default function FindingsPanel({ findings, warnings, disclaimer }) {
  const checklistItems = [
    'Confirm your exact Sum Insured from your official Star Health Premier Policy Schedule (Options start from ₹10 Lakh).',
    'Ask the hospital admission desk: "Does your hospital charge higher doctor/OT/procedure rates for higher room categories?"',
    'Verify if choosing a room at or below 1% of Sum Insured eliminates proportionate deductions entirely.',
    'If your policy tenure is under 24 months, confirm whether prior continuous insurance portability applies to waive the Specified Disease Waiting Period (Code Excl 02).',
    'Request an itemized hospital estimate separating room rent, doctor fees, OT charges, medicines, and consumables.',
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm space-y-5">
      {/* Critical Warnings */}
      {warnings && warnings.length > 0 && (
        <div>
          <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <h3 className="text-sm font-semibold text-slate-900">Critical Policy Discrepancies & Warnings</h3>
          </div>
          <div className="space-y-2 mt-2.5">
            {warnings.map((warning, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2 text-xs text-rose-800"
              >
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span className="leading-relaxed font-medium">{warning}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rule Engine Findings */}
      {findings && findings.length > 0 && (
        <div>
          <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <Info className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-slate-900">Rule Engine Analysis Findings</h3>
          </div>
          <div className="space-y-1.5 mt-2.5">
            {findings.map((finding, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-slate-700"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0"></span>
                <span className="leading-relaxed">{finding}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patient Action Checklist */}
      <div>
        <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
          <CheckSquare className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-semibold text-slate-900">Pre-Admission Patient Action Checklist</h3>
        </div>
        <p className="text-xs text-slate-500 mt-1.5">
          Verify these specific points with the hospital TPA / billing desk before signing admission consent:
        </p>
        <div className="space-y-2 mt-2.5">
          {checklistItems.map((item, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-slate-700"
            >
              <div className="h-4 w-4 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
                <Check className="w-3 h-3 stroke-[3]" />
              </div>
              <span className="leading-relaxed">{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Regulatory Disclaimer */}
      <div className="pt-3 border-t border-slate-100 text-center">
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Disclaimer: {disclaimer || "BimaSakshi provides informational policy pre-audit assistance. It does not replace the insurer's official claim decision."}
        </p>
      </div>
    </div>
  );
}
