import React from 'react';
import { BrainCircuit, AlertTriangle, HelpCircle, User, Calendar, Bed, Stethoscope, Sparkles, CheckCircle2, ShieldCheck, DollarSign } from 'lucide-react';

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
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
          <HelpCircle className="w-3 h-3 text-amber-600" />
          Not provided
        </span>
      );
    }
    return (
      <span className="font-semibold text-slate-900 text-xs font-mono tabular-nums">
        {typeof value === 'boolean' ? (value ? 'Yes / Confirmed' : 'No') : `${value} ${unit}`.trim()}
      </span>
    );
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-[#0F766E]" />
          <h3 className="font-heading text-base font-bold text-slate-900 tracking-tight">
            Extracted Insurance Parameters
          </h3>
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

        {/* Sum Insured */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <DollarSign className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Sum Insured</span>
          </div>
          <div>
            {info.sum_insured ? (
              <span className="font-semibold text-slate-900 text-xs font-mono tabular-nums">
                {formatINR(info.sum_insured)}
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Daily Room Rent */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <Bed className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Room Rent / Day</span>
          </div>
          <div>
            {info.selected_room_rent_per_day ? (
              <span className="font-semibold text-slate-900 text-xs font-mono tabular-nums">
                {formatINR(info.selected_room_rent_per_day)}
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Hospital Advance Deposit */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-medium">Hospital Deposit</span>
          </div>
          <div>
            {info.hospital_deposit ? (
              <span className="font-semibold text-slate-900 text-xs font-mono tabular-nums">
                {formatINR(info.hospital_deposit)}
              </span>
            ) : (
              <span className="text-xs text-slate-400">None stated</span>
            )}
          </div>
        </div>

        {/* Differential Billing Status */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-600">
            <ShieldCheck className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Differential Billing</span>
          </div>
          <div>
            {info.hospital_differential_billing === true ? (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                Practiced by Hospital
              </span>
            ) : info.hospital_differential_billing === false ? (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                Uniform Billing
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                Unconfirmed
              </span>
            )}
          </div>
        </div>

        {/* Diagnosis / Condition */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between sm:col-span-2">
          <div className="flex items-center gap-2 text-slate-600">
            <Stethoscope className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Stated Diagnosis</span>
          </div>
          <div className="text-right">
            {info.diagnosis_or_condition ? (
              <span className="font-semibold text-slate-900 text-xs">
                {info.diagnosis_or_condition}
              </span>
            ) : (
              renderBadge(null)
            )}
          </div>
        </div>

        {/* Treatment / Procedure */}
        {info.treatment_type && (
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between sm:col-span-2">
            <div className="flex items-center gap-2 text-slate-600">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <span className="text-xs font-medium">Treatment / Procedure</span>
            </div>
            <span className="font-semibold text-slate-900 text-xs">
              {info.treatment_type}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
