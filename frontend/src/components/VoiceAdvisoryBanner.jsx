import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, RotateCcw, Volume2, Copy, Check, Download, Sparkles } from 'lucide-react';

export default function VoiceAdvisoryBanner({ tts }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState(null);
  const [copied, setCopied] = useState(false);
  const audioRef = useRef(null);

  // Convert Base64 to Blob URL when tts changes
  useEffect(() => {
    if (tts?.audio_base64) {
      try {
        const byteCharacters = atob(tts.audio_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: tts.mime_type || 'audio/wav' });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        return () => {
          URL.revokeObjectURL(url);
        };
      } catch (err) {
        console.error('Failed to decode base64 audio:', err);
      }
    } else {
      setAudioUrl(null);
    }
  }, [tts]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const handleReplay = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleCopyText = () => {
    if (tts?.spoken_text) {
      navigator.clipboard.writeText(tts.spoken_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatTime = (timeInSec) => {
    if (isNaN(timeInSec)) return '00:00';
    const mins = Math.floor(timeInSec / 60);
    const secs = Math.floor(timeInSec % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!tts || (!tts.spoken_text && !tts.audio_base64)) {
    return null;
  }

  return (
    <div className="bg-white border border-blue-200 rounded-xl p-5 sm:p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <Volume2 className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                Hindi Voice Advisory
              </h3>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Live Synthesized
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Clear, patient-friendly guidance spoken in Hindi via Gnani Timbre v2.5
            </p>
          </div>
        </div>

        {/* Technical Metadata Tags */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
            Model: {tts.model || 'timbre-v2.5'}
          </span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
            Voice: Nalini (hi-IN)
          </span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200">
            48 kHz PCM
          </span>
        </div>
      </div>

      {/* Audio Player Controls */}
      {audioUrl && (
        <div className="mt-4 p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center gap-3 sm:gap-4">
          <audio
            ref={audioRef}
            src={audioUrl}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={handleEnded}
            className="hidden"
          />

          {/* Controls: Play & Replay */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={togglePlay}
              className="h-10 w-10 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors cursor-pointer shadow-xs"
              aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 ml-0.5 fill-current" />}
            </button>
            <button
              type="button"
              onClick={handleReplay}
              title="Replay from start"
              className="h-8 w-8 rounded-full bg-white hover:bg-slate-100 text-slate-600 border border-slate-200 flex items-center justify-center transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Time Scrubber */}
          <div className="flex-1 w-full flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs font-mono text-slate-500">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
            <input
              type="range"
              min="0"
              max={duration || 1}
              step="0.05"
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          {/* Download Action */}
          <a
            href={audioUrl}
            download="bimasakshi_hindi_advisory.wav"
            className="px-3 py-1.5 rounded-md bg-white hover:bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700 flex items-center gap-1.5 transition-colors shrink-0 shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Download WAV</span>
          </a>
        </div>
      )}

      {/* Hindi Spoken Text Transcript */}
      {tts.spoken_text && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Hindi Advisory Transcript
            </span>
            <button
              type="button"
              onClick={handleCopyText}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-slate-100 cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-emerald-700 font-medium">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy Text</span>
                </>
              )}
            </button>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-800 font-devanagari text-sm sm:text-base leading-relaxed break-words">
            "{tts.spoken_text}"
          </div>
        </div>
      )}
    </div>
  );
}
