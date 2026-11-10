/**
 * BimaSakshi Frontend API Client
 * Connects to the FastAPI backend at /api and /health
 */

const API_BASE = ''; // Proxied via Vite to http://127.0.0.1:8000

/**
 * Health check endpoint
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch('/health', {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend health check failed:', err);
    return { status: 'offline', vector_store_initialized: false, error: err.message };
  }
}

/**
 * Get active policy vector store details
 */
export async function getPolicyStatus() {
  try {
    const res = await fetch('/api/policy/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to get policy status:', err);
    throw err;
  }
}

/**
 * Perform semantic search on policy clauses
 */
export async function searchPolicyClauses(query, topK = 3) {
  const res = await fetch('/api/policy/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Search failed with status ${res.status}`);
  }
  return await res.json();
}

/**
 * Complete End-to-End Voice Claim Analysis Pipeline
 * @param {Blob|File} audioBlob - Audio recording or file
 * @param {string} [filename='recording.wav'] - Audio filename
 * @param {string} [policyId] - Optional policy identifier
 */
export async function analyzeAudioClaim(audioBlob, filename = 'recording.wav', policyId = null) {
  const formData = new FormData();
  formData.append('audio', audioBlob, filename);
  if (policyId) {
    formData.append('policy_id', policyId);
  }

  const res = await fetch('/api/analyze-audio', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = `Analysis request failed (HTTP ${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Keep default error detail
    }
    throw new Error(errorDetail);
  }

  return await res.json();
}

