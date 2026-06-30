import { useState, useRef } from "react";
import client from "../api/client";

export default function VoiceCheckIn({ onChangesApplied }) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [processing, setProcessing] = useState(false);
  const [proposedChanges, setProposedChanges] = useState(null);
  const recognitionRef = useRef(null);

  const startRecording = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert("Voice input is not supported in this browser. Please try Chrome.");
      return;
    }

    const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = false;
    recognitionRef.current.lang = 'en-US';

    recognitionRef.current.onstart = () => {
      setIsRecording(true);
      setTranscript("");
    };

    recognitionRef.current.onresult = (event) => {
      const current = event.resultIndex;
      const t = event.results[current][0].transcript;
      setTranscript(t);
      handleVoiceSubmit(t);
    };

    recognitionRef.current.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsRecording(false);
    };

    recognitionRef.current.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current.start();
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const handleVoiceSubmit = async (finalTranscript) => {
    if (!finalTranscript) return;
    setProcessing(true);
    try {
      const res = await client.post('/engagement/checkin/voice', { transcript: finalTranscript });
      setProposedChanges(res.data);
    } catch (err) {
      console.error("Failed to process voice check-in:", err);
      alert("Failed to process voice check-in.");
    } finally {
      setProcessing(false);
    }
  };

  const confirmChange = async (change, isApproved) => {
    if (isApproved) {
      try {
        await client.patch(`/steps/${change.step_id}`, { status: change.proposed_status });
      } catch (err) {
        console.error("Failed to apply change:", err);
        alert("Failed to apply change to step " + change.step_id);
      }
    }
    
    // Remove from proposed list
    setProposedChanges(prev => {
      const newChanges = prev.proposed_changes.filter(c => c.step_id !== change.step_id);
      if (newChanges.length === 0) {
        if (onChangesApplied) onChangesApplied();
        return null;
      }
      return { ...prev, proposed_changes: newChanges };
    });
  };

  const cancelAll = () => {
    setProposedChanges(null);
    setTranscript("");
  };

  return (
    <div className="voice-checkin-widget mb-6 p-4 bg-neutral-900 border border-neutral-700 rounded shadow-md">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold text-white">Daily Check-In 🎙️</h2>
        {isRecording ? (
          <button 
            onClick={stopRecording}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded font-medium animate-pulse"
          >
            <span className="w-2 h-2 bg-white rounded-full"></span>
            Recording... (Click to stop)
          </button>
        ) : (
          <button 
            onClick={startRecording}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded font-medium transition-colors"
            disabled={processing || proposedChanges}
          >
            {processing ? "Processing..." : "Start Voice Check-In"}
          </button>
        )}
      </div>
      <p className="text-neutral-400 text-sm">
        Tell me what you worked on today, and I'll figure out which tasks to update.
      </p>

      {proposedChanges && (
        <div className="mt-4 p-4 border border-indigo-500/30 bg-indigo-950/20 rounded">
          <h3 className="font-semibold text-indigo-300 mb-2">Here's what I understood:</h3>
          <p className="text-xs text-neutral-400 italic mb-4">"{proposedChanges.understood_transcript}"</p>
          
          {proposedChanges.proposed_changes.length === 0 ? (
            <p className="text-sm text-neutral-300">I didn't detect any specific status updates from what you said.</p>
          ) : (
            <div className="space-y-3">
              {proposedChanges.proposed_changes.map(change => (
                <div key={change.step_id} className="bg-neutral-800 p-3 rounded border border-neutral-700">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="text-sm font-medium text-white truncate max-w-[200px]" title={change.step_title}>{change.step_title}</div>
                      <div className="text-xs text-neutral-400 mt-1">{change.reasoning}</div>
                    </div>
                    <div className="bg-indigo-900/50 text-indigo-300 px-2 py-1 rounded text-xs">
                      Mark as: {change.proposed_status === 'done' ? 'Done' : 'In Progress'}
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end mt-3">
                    <button 
                      onClick={() => confirmChange(change, false)}
                      className="px-3 py-1 bg-neutral-700 hover:bg-neutral-600 text-white rounded text-xs"
                    >
                      Reject
                    </button>
                    <button 
                      onClick={() => confirmChange(change, true)}
                      className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs"
                    >
                      Confirm
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <button 
            onClick={cancelAll}
            className="mt-4 text-xs text-neutral-500 hover:text-neutral-300 underline"
          >
            Cancel / Clear
          </button>
        </div>
      )}
    </div>
  );
}
