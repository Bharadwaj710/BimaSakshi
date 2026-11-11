import React, { useState } from 'react';
import { AlertCircle, CheckSquare, ShieldAlert, Info, Check, Copy, HelpCircle, Shield } from 'lucide-react';

export default function FindingsPanel({ findings, warnings, disclaimer, checklist }) {
  const [copiedChecklist, setCopiedChecklist] = useState(false);

  const defaultChecklist = [
    'Confirm your exact Sum Insured from your official Star Health Premier Policy Schedule (Options start from ₹10 Lakh).',
    'Ask the hospital admission desk: "Does your hospital charge higher doctor/OT/procedure rates for higher room categories?"',
    'Verify if choosing a room at or below 1% of Sum Insured eliminates proportionate deductions entirely.',
    'If your policy tenure is under 24 months, confirm whether prior continuous insurance portability applies to waive the Specified Disease Waiting Period (Code Excl 02).',
    'Request an itemized hospital estimate separating room rent, doctor fees, OT charges, medicines, and consumables.',
  ];

  const checklistItems = checklist && checklist.length > 0 ? checklist : defaultChecklist;

  const handleCopyChecklist = () => {
    const text = checklistItems.map((item, idx) => `${idx + 1}. ${item}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopiedChecklist(true);
    setTimeout(() => setCopiedChecklist(false), 2000);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs space-y-5">
      {/* Critical Warnings & Deductions Risks */}
      {warnings && warnings.length > 0 && (
        <div>
          <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <h3 className="font-heading text-sm font-bold text-slate-900 tracking-tight">
              Policy Conditions & Potential Deduction Risks
            </h3>
          </div>
          <div className="space-y-2 mt-2.5">
            {warnings.map((warning, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-rose-50/70 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-900"
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
            <Info className="w-4 h-4 text-[#0F766E]" />
            <h3 className="font-heading text-sm font-bold text-slate-900 tracking-tight">
              Pre-Audit Findings
            </h3>
          </div>
          <div className="space-y-1.5 mt-2.5">
            {findings.map((finding, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-start gap-2.5 text-xs text-slate-700"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-[#0F766E] mt-1.5 shrink-0"></span>
                <span className="leading-relaxed">{finding}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patient Action Checklist */}
      <div>
        <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-emerald-600" />
            <h3 className="font-heading text-sm font-bold text-slate-900 tracking-tight">
              Pre-Admission Patient Action Checklist
            </h3>
          </div>

          <button
            type="button"
            onClick={handleCopyChecklist}
            className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-slate-100 cursor-pointer"
          >
            {copiedChecklist ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700 font-medium">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Checklist</span>
              </>
            )}
          </button>
        </div>

        <p className="text-xs text-slate-500 mt-1.5">
          Verify these specific points with the hospital TPA or admission desk before signing consent:
        </p>

        <div className="space-y-2 mt-2.5">
          {checklistItems.map((item, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-start gap-2.5 text-xs text-slate-800"
            >
              <div className="h-4 w-4 rounded bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 mt-0.5 font-bold text-[10px]">
                {idx + 1}
              </div>
              <span className="leading-relaxed font-normal">{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Statutory Disclaimer */}
      <div className="pt-3 border-t border-slate-100 flex items-start gap-2 text-[11px] text-slate-500">
        <Shield className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
        <span className="leading-relaxed">
          {disclaimer || 'BimaSakshi provides informational policy pre-audit assistance. It does not replace the insurer’s official claim decision or cashless pre-authorisation sanction.'}
        </span>
      </div>
    </div>
  );
}
