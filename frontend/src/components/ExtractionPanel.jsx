import React from 'react';
import { BrainCircuit, AlertTriangle, HelpCircle, User, Calendar, Bed, Stethoscope, ShieldAlert, Sparkles, CheckCircle2 } from 'lucide-react';

export default function ExtractionPanel({ info }) {
  if (!info) return null;

  // Format currency in Indian numbering format
  const formatINR = (val) => {
    if (val === null || val === undefined) return null;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const renderBadge = (value, unit = '') => {
    if (value === null || value === undefined) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <HelpCircle className="w-3 h-3" />
          Not provided
        </span>
      );
    }
    return (
      <span className="font-semibold text-slate-800 text-xs">
        {typeof value === 'boolean' ? (value ? 'Yes / Confirmed' : 'No') : `${value} ${unit}`.trim()}
      </span>
    );
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-blue-600" />
          <h3 className="text-base font-semibold text-slate-900">Extracted Insurance Parameters</h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
          Gemini 2.5 Flash
        </span>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Structured parameters parsed directly from user voice transcript using strict Pydantic schemas.
      </p>

      {/* Grid of Extracted Variables */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-3.5">
        {/* Patient Age */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <User className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Patient Age</span>
          </div>
          <div>{renderBadge(info.age, 'Years')}</div>
        </div>

        {/* Policy Tenure */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Policy Tenure</span>
          </div>
          <div>{renderBadge(info.policy_tenure_months, 'Months')}</div>
        </div>

        {/* Diagnosis / Condition */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <Stethoscope className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Condition</span>
          </div>
          <div className="text-right">
            {info.diagnosis_or_condition ? (
              <span className="font-semibold text-slate-800 text-xs">
                {info.diagnosis_or_condition}
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Treatment Type */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <Sparkles className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Treatment</span>
          </div>
          <div className="text-right">
            {info.treatment_type ? (
              <span className="font-semibold text-slate-800 text-xs">{info.treatment_type}</span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Requested Room Rent */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <Bed className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Requested Room Rent</span>
          </div>
          <div>
            {info.selected_room_rent_per_day !== null && info.selected_room_rent_per_day !== undefined ? (
              <span className="font-bold text-rose-600 text-xs font-mono">
                {formatINR(info.selected_room_rent_per_day)} / day
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Hospital Advance Deposit */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <ShieldAlert className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Hospital Advance Deposit</span>
          </div>
          <div>
            {info.hospital_deposit !== null && info.hospital_deposit !== undefined ? (
              <span className="font-bold text-blue-700 text-xs font-mono">
                {formatINR(info.hospital_deposit)} (Admission Security)
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Sum Insured */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <ShieldAlert className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Sum Insured</span>
          </div>
          <div>
            {info.sum_insured !== null && info.sum_insured !== undefined ? (
              <span className="font-bold text-emerald-700 text-xs font-mono">
                {formatINR(info.sum_insured)}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                <HelpCircle className="w-3 h-3" />
                Not stated (Schedule Required)
              </span>
            )}
          </div>
        </div>

        {/* Hospital Differential Billing */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between sm:col-span-2">
          <div className="flex items-center gap-2 text-slate-600">
            <HelpCircle className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Hospital Differential Billing Practice</span>
          </div>
          <div>
            {info.hospital_differential_billing === true && (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
                Practiced by Hospital (Higher tier = higher charge)
              </span>
            )}
            {info.hospital_differential_billing === false && (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                Uniform Billing (No Differential)
              </span>
            )}
            {info.hospital_differential_billing === null && (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                Unconfirmed • Inquire at Hospital TPA Desk
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Dynamic Intent Badges */}
      {info.identified_intents && info.identified_intents.length > 0 && (
        <div className="mt-3.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
            Identified Insurance Intents ({info.identified_intents.length}):
          </span>
          <div className="flex flex-wrap gap-1.5">
            {info.identified_intents.map((intent, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded text-xs font-medium bg-white text-blue-700 border border-blue-200 shadow-xs"
              >
                {intent.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Preserved Units & Quantities */}
      {info.units_and_amounts && info.units_and_amounts.length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
            Extracted Quantities & Units:
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {info.units_and_amounts.map((item, idx) => (
              <div key={idx} className="p-2 rounded bg-white border border-slate-200 text-xs">
                <span className="text-slate-400 block text-[10px] uppercase font-mono">{item.parameter}</span>
                <span className="font-semibold text-slate-800">{item.stated_value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decomposed ChromaDB Queries */}
      {info.retrieval_queries && info.retrieval_queries.length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
            Decomposed Retrieval Queries ({info.retrieval_queries.length}):
          </span>
          <div className="space-y-1">
            {info.retrieval_queries.map((q, idx) => (
              <div key={idx} className="p-2 rounded bg-white border border-slate-200 font-mono text-[11px] text-slate-700 flex items-start gap-2">
                <span className="text-blue-600 shrink-0 font-bold">Q{idx + 1}:</span>
                <span className="leading-relaxed">{q}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing Information Alerts */}
      {info.missing_information && info.missing_information.length > 0 && (
        <div className="mt-3.5 p-3 rounded-lg bg-amber-50/70 border border-amber-200">
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-800 mb-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>Missing Claim Parameters Requiring Schedule Verification:</span>
          </div>
          <ul className="space-y-1 text-xs text-amber-900">
            {info.missing_information.map((item, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-amber-600 mt-1">•</span>
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
