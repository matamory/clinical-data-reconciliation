// Governing: SPEC-0001 REQ "DaisyUI Component Integration", SPEC-0001 REQ "Frontend–Backend API Proxy"
import React, { useState } from 'react';

function ReconciliationForm() {
  const [formData, setFormData] = useState({
    age: '',
    conditions: '',
    recentLabs: '',
    sources: [{ system: '', medication: '', lastUpdated: '', reliability: 'medium' }]
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFieldChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSourceChange = (index, field, value) => {
    const newSources = [...formData.sources];
    newSources[index][field] = value;
    setFormData(prev => ({ ...prev, sources: newSources }));
  };

  const addSource = () => {
    setFormData(prev => ({
      ...prev,
      sources: [...prev.sources, { system: '', medication: '', lastUpdated: '', reliability: 'medium' }]
    }));
  };

  const removeSource = (index) => {
    if (formData.sources.length > 1) {
      setFormData(prev => ({
        ...prev,
        sources: prev.sources.filter((_, i) => i !== index)
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const payload = {
        patient_context: {
          age: parseInt(formData.age) || 0,
          conditions: formData.conditions.split(',').map(c => c.trim()).filter(c => c),
          recent_labs: formData.recentLabs.split(',').map(lab => {
            const parts = lab.trim().split(':');
            return {
              name: parts[0] || '',
              value: { text_value: parts[1] || null, numeric_value: null, unit: parts[2] || null }
            };
          }).filter(l => l.name)
        },
        sources: formData.sources.map(source => ({
          system: source.system,
          medication: source.medication,
          last_updated: source.lastUpdated ? new Date(source.lastUpdated).toISOString().split('T')[0] : null,
          last_filled: null,
          source_reliability: source.reliability
        })).filter(s => s.system && s.medication)
      };

      // Governing: SPEC-0001 REQ "Frontend–Backend API Proxy" — uses CRA proxy (localhost:5000)
      const response = await fetch('/api/reconcile/medication', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Governing: SPEC-0001 REQ "DaisyUI Component Integration" — confidence → progress/stat, safety → badge/alert
  const confidencePct = result ? Math.round(result.confidence_score * 100) : 0;
  const confidenceColor = confidencePct > 75 ? 'progress-success' : confidencePct > 50 ? 'progress-warning' : 'progress-error';

  const safetyAlertClass = {
    PASSED: 'alert-success',
    FAILED: 'alert-error',
    REVIEW_REQUIRED: 'alert-warning',
  }[result?.clinical_safety_check] || 'alert-info';

  const safetyBadgeClass = {
    PASSED: 'badge-success',
    FAILED: 'badge-error',
    REVIEW_REQUIRED: 'badge-warning',
  }[result?.clinical_safety_check] || 'badge-ghost';

  return (
    <div className="space-y-6">
      <div className="card bg-base-100 shadow">
        <div className="card-body">
          <h2 className="card-title text-xl">Medication Reconciliation</h2>
          <p className="text-base-content/70">
            Enter patient information and medication sources from different systems for reconciliation.
          </p>

          <form onSubmit={handleSubmit} className="space-y-6 mt-2">
            {/* Patient Information */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Patient Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-control">
                  <label className="label"><span className="label-text">Age</span></label>
                  <input
                    type="number"
                    name="age"
                    className="input input-bordered"
                    value={formData.age}
                    onChange={handleFieldChange}
                    placeholder="e.g., 45"
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Conditions</span></label>
                  <input
                    type="text"
                    name="conditions"
                    className="input input-bordered"
                    value={formData.conditions}
                    onChange={handleFieldChange}
                    placeholder="e.g., Hypertension, Type 2 Diabetes"
                  />
                </div>
              </div>
              <div className="form-control mt-4">
                <label className="label"><span className="label-text">Recent Labs (name:value:unit)</span></label>
                <textarea
                  name="recentLabs"
                  className="textarea textarea-bordered"
                  value={formData.recentLabs}
                  onChange={handleFieldChange}
                  placeholder="e.g., HbA1c:7.2:%, BP:120/80:mmHg"
                  rows={3}
                />
              </div>
            </div>

            {/* Medication Sources */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Medication Sources</h3>
              <div className="space-y-4">
                {formData.sources.map((source, index) => (
                  <div key={index} className="card bg-base-200">
                    <div className="card-body p-4">
                      <div className="flex justify-between items-center mb-3">
                        <h4 className="font-medium">Source {index + 1}</h4>
                        {formData.sources.length > 1 && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-xs text-error"
                            onClick={() => removeSource(index)}
                          >
                            Remove
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="form-control">
                          <label className="label"><span className="label-text">System</span></label>
                          <input
                            type="text"
                            className="input input-bordered input-sm"
                            value={source.system}
                            onChange={(e) => handleSourceChange(index, 'system', e.target.value)}
                            placeholder="e.g., Hospital EMR"
                          />
                        </div>
                        <div className="form-control">
                          <label className="label"><span className="label-text">Medication</span></label>
                          <input
                            type="text"
                            className="input input-bordered input-sm"
                            value={source.medication}
                            onChange={(e) => handleSourceChange(index, 'medication', e.target.value)}
                            placeholder="e.g., Metformin 500mg"
                          />
                        </div>
                        <div className="form-control">
                          <label className="label"><span className="label-text">Last Updated</span></label>
                          <input
                            type="date"
                            className="input input-bordered input-sm"
                            value={source.lastUpdated}
                            onChange={(e) => handleSourceChange(index, 'lastUpdated', e.target.value)}
                          />
                        </div>
                        <div className="form-control">
                          <label className="label"><span className="label-text">Reliability</span></label>
                          <select
                            className="select select-bordered select-sm"
                            value={source.reliability}
                            onChange={(e) => handleSourceChange(index, 'reliability', e.target.value)}
                          >
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <button type="button" className="btn btn-outline btn-sm mt-3" onClick={addSource}>
                + Add Another Source
              </button>
            </div>

            <button type="submit" className="btn btn-primary w-full" disabled={loading}>
              {loading ? <span className="loading loading-spinner loading-sm"></span> : null}
              {loading ? 'Reconciling...' : 'Reconcile Medication'}
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <span><strong>Error:</strong> {error}</span>
        </div>
      )}

      {result && (
        <div className="card bg-base-100 shadow">
          <div className="card-body">
            <h2 className="card-title text-xl">Reconciliation Result</h2>

            {/* Confidence — DaisyUI stat + progress */}
            <div className="stats shadow w-full mb-4">
              <div className="stat">
                <div className="stat-title">Reconciled Medication</div>
                <div className="stat-value text-lg">{result.reconciled_medication || 'Unknown'}</div>
              </div>
              <div className="stat">
                <div className="stat-title">Confidence Score</div>
                <div className="stat-value text-2xl">{confidencePct}%</div>
                <div className="stat-desc mt-1">
                  <progress className={`progress ${confidenceColor} w-full`} value={confidencePct} max="100"></progress>
                </div>
              </div>
            </div>

            {/* Safety Check — DaisyUI badge + alert */}
            <div className={`alert ${safetyAlertClass} mb-4`}>
              <span className="font-semibold">Safety Check:</span>
              <span className={`badge ${safetyBadgeClass} ml-2`}>{result.clinical_safety_check}</span>
            </div>

            {result.reasoning && (
              <div className="mb-4">
                <h4 className="font-semibold mb-1">Reasoning</h4>
                <p className="text-base-content/80">{result.reasoning}</p>
              </div>
            )}

            {result.recommended_actions && result.recommended_actions.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Recommended Actions</h4>
                <ul className="list-disc list-inside space-y-1">
                  {result.recommended_actions.map((action, idx) => (
                    <li key={idx} className="text-base-content/80">{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ReconciliationForm;
