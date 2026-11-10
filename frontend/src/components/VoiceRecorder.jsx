import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Upload, Play, Pause, RotateCcw, Volume2, CheckCircle2, AlertCircle, FileAudio, Sparkles } from 'lucide-react';

const PRESET_SCENARIOS = [
  {
    id: 'calculi',
    name: 'Scenario A: Kidney Calculi & Room Limit',
    shortTitle: 'Scenario A: Calculi & Room Limit',
    category: 'Code Excl 02 & Room Limit',
    file: '/calculi_scenario.wav',
    filename: 'calculi_and_room_scenario.wav',
    hindiPrompt: 'मेरे एज 52 इयर्स है और मेरे पास स्टार हेल्थ प्रीमियर की 10,00,000 की पॉलिसी है जो 14 मंथ पुराना है मुझे किडनी स्टोन सर्जरी करवाना है रूम रेंट 30,000 पर डे और हॉस्पिटल डिफरेंट रूम कैटेगरीज़ के हिसाब से बिल करता है क्या प्रोपोर्शनेट डिडक्शन 24 मंथ वेटिंग पीरियड अप्लाई होगा?',
    details: [
      { label: 'Sum Insured', value: '₹10,00,000 (Stated)' },
      { label: 'Procedure', value: 'Kidney Calculi Surgery' },
      { label: 'Policy Tenure', value: '14 Months (Under 24 Mo)' },
      { label: 'Room Requested', value: '₹30,000 / day (Exceeds 1%)' },
      { label: 'Billing Type', value: 'Differential Billing Practiced' },
    ],
  },
  {
    id: 'accident',
    name: 'Scenario B: Accident Waiting-Period Exception',
    shortTitle: 'Scenario B: Accident Waiver',
    category: 'Code Excl 02 Exception',
    file: '/accident_scenario.wav',
    filename: 'accident_question.wav',
    hindiPrompt: 'क्या एक्सीडेंट के कारण होने वाली सर्जरी पर भी 24 महीने का वेटिंग पीरियड लागू होता है?',
    details: [
      { label: 'Primary Intent', value: 'Accident Exception Inquiry' },
      { label: 'Target Clause', value: 'STAR-PREMIER-WAIT-002 (Page 6)' },
      { label: 'Applicability', value: 'Exclusion waived for accident claims' },
      { label: 'Expected Outcome', value: 'Immediate Coverage (No Waiting Period)' },
    ],
  },
  {
    id: 'robotic',
    name: 'Scenario C: Modern Robotic Surgery Limit',
    shortTitle: 'Scenario C: Robotic Surgery Limit',
    category: 'Coverage 14 Modern Treatment',
    file: '/robotic_scenario.wav',
    filename: 'robotic_surgery_inquiry.wav',
    hindiPrompt: 'मेरी उम्र 58 वर्ष है और स्टार हेल्थ प्रीमियर 10 लाख की पॉलिसी 3 साल पुरानी है। मुझे रोबोटिक सर्जरी करवानी है जिसका एस्टिमेट 6 लाख रुपये है। क्या इस पर कोई सब-लिमिट लागू होगी?',
    details: [
      { label: 'Procedure', value: 'Robotic Surgery (Modern Treatment)' },
      { label: 'Sum Insured', value: '₹10,00,000 (Stated)' },
      { label: 'Estimated Cost', value: '₹6,00,000' },
      { label: 'Sub-Limit Clause', value: 'STAR-PREMIER-MODERN-014 (Page 4)' },
      { label: 'Cap Rule', value: '50% of Sum Insured (Max ₹5,00,000)' },
    ],
  },
  {
    id: 'ambiguous_kidney',
    name: 'Scenario D: Ambiguous Diagnosis Clarification',
    shortTitle: 'Scenario D: Ambiguous Condition',
    category: 'Information Safeguard',
    file: '/ambiguous_kidney_scenario.wav',
    filename: 'ambiguous_kidney_query.wav',
    hindiPrompt: 'मुझे किडनी की प्रॉब्लम है और डॉक्टर ने ऑपरेशन सजेस्ट किया है। क्या मेरी पॉलिसी में यह कवर होगा?',
    details: [
      { label: 'Stated Condition', value: 'Generic "Kidney Problem"' },
      { label: 'Diagnosis Status', value: 'Ambiguous / Unspecified' },
      { label: 'Safeguard Rule', value: 'Does not auto-map to calculi' },
      { label: 'Expected Response', value: 'Insufficient info • Requests exact diagnosis' },
    ],
  },
  {
    id: 'deposit_benefits',
    name: 'Scenario E: Hospital Deposit & Benefits Inquiry',
    shortTitle: 'Scenario E: Deposit & Benefits',
    category: 'Multi-Intent & Advance Deposit',
    file: '/deposit_scenario.wav',
    filename: 'deposit_and_benefits_query.wav',
    hindiPrompt: 'मेरी उम्र 24 वर्ष है, मुझे किडनी स्टोन सर्जरी करवानी है और मेरे पास स्टार हेल्थ इंश्योरेंस है। अस्पताल मुझसे 30,000 रुपये का डिपॉजिट मांग रहा है। मेरी पॉलिसी में मुझे क्या बेनिफिट्स मिलेंगे?',
    details: [
      { label: 'Patient Age', value: '24 Years (Eligibility Ambiguity)' },
      { label: 'Procedure', value: 'Kidney Calculi Surgery' },
      { label: 'Advance Deposit', value: '₹30,000 (Advance Security)' },
      { label: 'Cashless Mechanism', value: 'Adjusted/Refunded upon TPA sanction' },
      { label: 'Benefits Scope', value: 'In-Patient Hospitalization (Coverage 1)' },
    ],
  },
];

export default function VoiceRecorder({ onAnalyze, isAnalyzing }) {
  const [activeTab, setActiveTab] = useState('record'); // 'record' | 'upload' | 'sample'
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioFileName, setAudioFileName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedScenarioId, setSelectedScenarioId] = useState('calculi');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);
  const fileInputRef = useRef(null);

  // Clean up blob URLs when changed
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  // Recording Timer
  useEffect(() => {
    if (isRecording) {
      setRecordingDuration(0);
      timerIntervalRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    }
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [isRecording]);

  const formatSeconds = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Start MediaRecorder
  const startRecording = async () => {
    setErrorMsg('');
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        if (blob.size < 500) {
          setErrorMsg('Recorded audio was too short or empty. Please try speaking again.');
          setAudioBlob(null);
          setAudioUrl(null);
          return;
        }
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        const ext = mimeType.includes('webm') ? 'webm' : (mimeType.includes('ogg') ? 'ogg' : 'wav');
        setAudioFileName(`recording_${Date.now()}.${ext}`);
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start(100);
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone access denied:', err);
      setErrorMsg('Microphone permission denied or microphone not found. You can upload an audio file or try the sample scenarios.');
    }
  };

  // Stop MediaRecorder
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Handle File Upload
  const handleFileUpload = (e) => {
    setErrorMsg('');
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('audio/') && !file.name.match(/\.(wav|mp3|m4a|aac|ogg|webm)$/i)) {
      setErrorMsg('Please select a valid audio file (.wav, .mp3, .m4a, .ogg).');
      return;
    }

    setAudioBlob(file);
    setAudioFileName(file.name);
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
  };

  // Load Authentic Preset Scenario
  const handleLoadScenario = async (scenarioId) => {
    setErrorMsg('');
    const scenario = PRESET_SCENARIOS.find((s) => s.id === scenarioId) || PRESET_SCENARIOS[0];
    setSelectedScenarioId(scenario.id);

    try {
      const res = await fetch(scenario.file);
      if (!res.ok) throw new Error(`Sample audio ${scenario.file} not found`);
      const blob = await res.blob();
      setAudioBlob(blob);
      setAudioFileName(scenario.filename);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (err) {
      console.error('Failed to load sample scenario:', err);
      setErrorMsg('Could not load sample audio file. Please try recording or uploading.');
    }
  };

  // Switch tab
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setErrorMsg('');
    if (tab === 'sample') {
      handleLoadScenario(selectedScenarioId);
    }
  };

  // Reset audio
  const handleResetAudio = () => {
    setAudioBlob(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setAudioFileName('');
    setErrorMsg('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Trigger Analysis
  const handleAnalyzeClick = () => {
    if (!audioBlob) {
      setErrorMsg('Please record voice, upload an audio file, or select a sample scenario first.');
      return;
    }
    onAnalyze(audioBlob, audioFileName || 'claim_voice.wav');
  };

  const currentScenario = PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) || PRESET_SCENARIOS[0];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Panel Header & Mode Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-blue-600" />
            Voice Claim Input
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit your planned hospitalization details in Hindi or Hinglish.
          </p>
        </div>

        {/* Input Mode Selector */}
        <div className="flex items-center p-1 rounded-lg bg-slate-100 border border-slate-200 text-xs">
          <button
            type="button"
            onClick={() => handleTabChange('record')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'record'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Mic className="w-3.5 h-3.5 text-blue-600" />
            Record Voice
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('upload')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'upload'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5 text-slate-500" />
            Upload File
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('sample')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'sample'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Sample Scenarios
          </button>
        </div>
      </div>

      {/* Mode 1: Record Voice */}
      {activeTab === 'record' && (
        <div className="py-6 flex flex-col items-center justify-center text-center">
          {!audioBlob ? (
            <div className="flex flex-col items-center max-w-sm">
              <div className="mb-4">
                <button
                  type="button"
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={isAnalyzing}
                  className={`h-16 w-16 rounded-full flex items-center justify-center transition-all ${
                    isRecording
                      ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-md'
                      : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:scale-105'
                  }`}
                  aria-label={isRecording ? 'Stop recording' : 'Start recording'}
                >
                  {isRecording ? (
                    <Square className="w-6 h-6 fill-current" />
                  ) : (
                    <Mic className="w-6 h-6" />
                  )}
                </button>
              </div>

              {isRecording ? (
                <div className="flex flex-col items-center gap-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
                    <span className="font-mono text-base font-semibold text-rose-600">
                      {formatSeconds(recordingDuration)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Recording audio... Click the red square when finished speaking.
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-800">Click to start voice recording</p>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Speak naturally. Example: "मेरी उम्र 52 वर्ष है, मुझे किडनी स्टोन सर्जरी करानी है, ₹30,000 प्रतिदिन का कमरा लेना है..."
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="w-full max-w-lg bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-medium text-slate-800">Voice recording captured ({audioFileName})</span>
                </div>
                <button
                  type="button"
                  onClick={handleResetAudio}
                  className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" /> Re-record
                </button>
              </div>
              <audio src={audioUrl} controls className="w-full h-9" />
            </div>
          )}
        </div>
      )}

      {/* Mode 2: Upload File */}
      {activeTab === 'upload' && (
        <div className="py-6">
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.ogg"
            onChange={handleFileUpload}
            className="hidden"
          />
          {!audioBlob ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-lg p-8 text-center cursor-pointer bg-slate-50/50 hover:bg-slate-50 transition-colors flex flex-col items-center justify-center gap-2 max-w-lg mx-auto"
            >
              <div className="h-10 w-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-1">
                <Upload className="w-5 h-5" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                Click to browse or drop an audio file
              </p>
              <p className="text-xs text-slate-500">
                Supported formats: WAV (recommended), MP3, M4A, OGG up to 25MB
              </p>
            </div>
          ) : (
            <div className="max-w-lg mx-auto bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span className="text-xs font-medium text-slate-800 truncate">{audioFileName}</span>
                </div>
                <button
                  type="button"
                  onClick={handleResetAudio}
                  className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 transition-colors shrink-0 ml-2"
                >
                  <RotateCcw className="w-3 h-3" /> Change File
                </button>
              </div>
              <audio src={audioUrl} controls className="w-full h-9" />
            </div>
          )}
        </div>
      )}

      {/* Mode 3: Sample Scenarios */}
      {activeTab === 'sample' && (
        <div className="py-4 space-y-3.5">
          {/* Scenario Selector Pills */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
            {PRESET_SCENARIOS.map((sc) => {
              const isSelected = sc.id === selectedScenarioId;
              return (
                <button
                  key={sc.id}
                  type="button"
                  onClick={() => handleLoadScenario(sc.id)}
                  className={`p-2.5 rounded-lg text-left transition-all border text-xs cursor-pointer ${
                    isSelected
                      ? 'bg-blue-50/80 border-blue-300 text-blue-900 ring-1 ring-blue-300'
                      : 'bg-slate-50 hover:bg-slate-100/80 border-slate-200 text-slate-700'
                  }`}
                >
                  <div className="font-semibold truncate">{sc.shortTitle}</div>
                  <div className="text-[11px] text-slate-500 truncate mt-0.5">{sc.category}</div>
                </button>
              );
            })}
          </div>

          {/* Active Scenario Card */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-700">
                  {currentScenario.category}
                </span>
                <h4 className="text-sm font-semibold text-slate-900 mt-0.5">
                  {currentScenario.name}
                </h4>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600 shrink-0">
                {currentScenario.filename}
              </span>
            </div>

            <div className="p-3 bg-white border border-slate-200 rounded-md text-xs text-slate-700 leading-relaxed font-devanagari">
              "{currentScenario.hindiPrompt}"
            </div>

            {/* Structured Parameters */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3 pt-3 border-t border-slate-200 text-[11px]">
              {currentScenario.details.map((item, idx) => (
                <div key={idx}>
                  <span className="text-slate-500 block">{item.label}</span>
                  <span className="font-medium text-slate-800">{item.value}</span>
                </div>
              ))}
            </div>

            {/* Audio Preview */}
            {audioUrl && (
              <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-center gap-3">
                <span className="text-xs text-slate-500 shrink-0 font-medium">Audio Preview:</span>
                <audio src={audioUrl} controls className="w-full h-8" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="mt-3 p-3 rounded-md bg-rose-50 border border-rose-200 flex items-start gap-2 text-xs text-rose-700">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Action Footer */}
      <div className="mt-4 pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="text-xs text-slate-500 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span>Audio transcribed with Gnani Prisma v2.5 STT</span>
        </div>

        <button
          type="button"
          onClick={handleAnalyzeClick}
          disabled={!audioBlob || isAnalyzing || isRecording}
          className={`w-full sm:w-auto px-5 py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-colors shadow-sm ${
            !audioBlob || isAnalyzing || isRecording
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
              : 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
          }`}
        >
          {isAnalyzing ? (
            <>
              <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>Analyzing Claim...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>Analyze Policy Claim</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
