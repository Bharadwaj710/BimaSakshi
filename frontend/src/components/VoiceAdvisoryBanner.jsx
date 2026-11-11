import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, RotateCcw, Volume2, Copy, Check, Download, Sparkles, Shield, AlertCircle } from 'lucide-react';

export default function VoiceAdvisoryBanner({ tts }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState(null);
  const [copied, setCopied] = useState(false);
  const audioRef = useRef(null);

  // Convert Base64 WAV from Timbre v2.5 to Blob URL
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
        console.error('Failed to decode base64 audio from Timbre:', err);
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
    <div className="bg-[#0F766E] text-white rounded-xl p-5 sm:p-6 shadow-md border border-[#115E59]">
      {/* Top Bar: Title & Technology Identity */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-teal-600/60">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-teal-800/80 text-teal-200 border border-teal-600/80 flex items-center justify-center shrink-0">
            <Volume2 className="w-5 h-5 text-teal-200" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading text-lg font-bold text-white tracking-tight">
                Hindi Voice Advisory
              </h3>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-teal-800 text-teal-200 border border-teal-600/70">
                Spoken Guidance
              </span>
            </div>
            <p className="text-xs text-teal-100/90 mt-0.5">
              Natural spoken pre-admission guidance generated directly from policy evidence
            </p>
          </div>
        </div>

        {/* Technical Badges */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-teal-800/90 text-teal-100 border border-teal-600/60">
            Gnani Timbre v2.5
          </span>
          <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-teal-800/90 text-teal-100 border border-teal-600/60">
            Voice: Nalini (hi-IN)
          </span>
          <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-teal-800/90 text-teal-100 border border-teal-600/60 hidden sm:inline">
            48 kHz WAV
          </span>
        </div>
      </div>

      {/* Audio Player Controls */}
      {audioUrl ? (
        <div className="mt-4 p-3.5 rounded-lg bg-teal-800/60 border border-teal-600/50 flex flex-col sm:flex-row items-center gap-3 sm:gap-4">
          <audio
            ref={audioRef}
            src={audioUrl}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={handleEnded}
            className="hidden"
          />

          {/* Action Buttons: Play/Pause & Replay */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={togglePlay}
              className="h-10 w-10 rounded-full bg-white text-[#0F766E] hover:bg-teal-50 flex items-center justify-center transition-colors cursor-pointer shadow-sm"
              aria-label={isPlaying ? 'Pause advisory audio' : 'Play advisory audio'}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 fill-current" />
              ) : (
                <Play className="w-5 h-5 ml-0.5 fill-current" />
              )}
            </button>
            <button
              type="button"
              onClick={handleReplay}
              title="Replay from start"
              className="h-8 w-8 rounded-full bg-teal-700/80 hover:bg-teal-700 text-teal-100 border border-teal-600/80 flex items-center justify-center transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Time Scrubber */}
          <div className="flex-1 w-full flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs font-mono text-teal-200">
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
              className="w-full h-1.5 bg-teal-900/80 rounded-lg appearance-none cursor-pointer accent-white"
            />
          </div>

          {/* Download Audio Action */}
          <a
            href={audioUrl}
            download="bimasakshi_hindi_advisory.wav"
            className="px-3 py-1.5 rounded-md bg-teal-700/80 hover:bg-teal-700 border border-teal-600/80 text-xs font-medium text-white flex items-center gap-1.5 transition-colors shrink-0 shadow-xs cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-teal-200" />
            <span>Download WAV</span>
          </a>
        </div>
      ) : tts.error ? (
        <div className="mt-4 p-3 rounded-lg bg-teal-800/40 border border-teal-600/50 flex items-center gap-2 text-xs text-amber-200">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-300" />
          <span>Audio synthesis unavailable ({tts.error}). Text advisory remains readable below.</span>
        </div>
      ) : null}

      {/* Hindi Spoken Text Transcript */}
      {tts.spoken_text && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-teal-200 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-teal-300" />
              Hindi Advisory Transcript (Devanagari)
            </span>
            <button
              type="button"
              onClick={handleCopyText}
              className="text-xs text-teal-200 hover:text-white flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-teal-800/80 cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-300" />
                  <span className="text-emerald-300 font-medium">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Text</span>
                </>
              )}
            </button>
          </div>
          <div className="p-4 rounded-lg bg-teal-800/50 border border-teal-600/40 text-teal-50 font-devanagari text-base sm:text-[17px] leading-relaxed break-words selection:bg-teal-900 selection:text-white">
            "{tts.spoken_text}"
          </div>
        </div>
      )}
    </div>
  );
}
