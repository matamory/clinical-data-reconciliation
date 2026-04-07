// Governing: SPEC-0001 REQ "DaisyUI Component Integration", SPEC-0001 REQ "Frontend–Backend API Proxy"
import React, { useState } from 'react';

const SCORE_BADGE = (score) => {
  if (score >= 90) return { badge: 'badge-success', progress: 'progress-success', label: 'Excellent' };
  if (score >= 75) return { badge: 'badge-info',    progress: 'progress-info',    label: 'Good' };
  if (score >= 60) return { badge: 'badge-warning', progress: 'progress-warning', label: 'Acceptable' };
  if (score >= 40) return { badge: 'badge-warning', progress: 'progress-warning', label: 'Poor' };
  return              { badge: 'badge-error',   progress: 'progress-error',   label: 'Critical' };
};

const SEVERITY_BADGE = { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' };
const SEVERITY_ALERT = { critical: 'alert-error', high: 'alert-warning', medium: 'alert-info', low: '' };

function ValidationForm() {
  const [formData, setFormData] = useState({
    name: '', dob: '', gender: '', medications: '', allergies: '',
    conditions: '', bloodPressure: '', heartRate: '', temperature: '', lastUpdated: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const payload = {
        demographics: {
          name: formData.name || null,
          dob: formData.dob || null,
          gender: formData.gender || null
        },
        medications: formData.medications.split(',').map(m => m.trim()).filter(m => m),
        allergies: formData.allergies.split(',').map(a => a.trim()).filter(a => a),
        conditions: formData.conditions.split(',').map(c => c.trim()).filter(c => c),
        vital_signs: {
          blood_pressure: formData.bloodPressure || null,
          heart_rate: formData.heartRate ? parseInt(formData.heartRate) : null,
          temperature: formData.temperature ? parseFloat(formData.temperature) : null,
          respiratory_rate: null
        },
        last_updated: formData.lastUpdated ? new Date(formData.lastUpdated).toISOString().split('T')[0] : null
      };

      // Governing: SPEC-0001 REQ "Frontend–Backend API Proxy" — uses CRA proxy (localhost:5000)
      const response = await fetch('/api/validate/data-quality', {
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

  const overall = result ? SCORE_BADGE(result.overall_score) : null;

  return (
    <div className="space-y-6">
      <div className="card bg-base-100 shadow">
        <div className="card-body">
          <h2 className="card-title text-xl">Data Quality Validation</h2>
          <p className="text-base-content/70">
            Validate patient data quality across four dimensions: completeness, validity, consistency, and timeliness.
          </p>

          <form onSubmit={handleSubmit} className="space-y-6 mt-2">
            {/* Demographics */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Demographics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="form-control">
                  <label className="label"><span className="label-text">Patient Name</span></label>
                  <input type="text" name="name" className="input input-bordered" value={formData.name} onChange={handleChange} placeholder="e.g., John Doe" />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Date of Birth</span></label>
                  <input type="date" name="dob" className="input input-bordered" value={formData.dob} onChange={handleChange} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Gender</span></label>
                  <select name="gender" className="select select-bordered" value={formData.gender} onChange={handleChange}>
                    <option value="">Select...</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Clinical Information */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Clinical Information</h3>
              <div className="space-y-3">
                <div className="form-control">
                  <label className="label"><span className="label-text">Medications (comma-separated)</span></label>
                  <textarea name="medications" className="textarea textarea-bordered" value={formData.medications} onChange={handleChange} placeholder="e.g., Metformin 500mg, Lisinopril 10mg" rows={2} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Allergies (comma-separated)</span></label>
                  <textarea name="allergies" className="textarea textarea-bordered" value={formData.allergies} onChange={handleChange} placeholder="e.g., Penicillin, Shellfish" rows={2} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Medical Conditions (comma-separated)</span></label>
                  <textarea name="conditions" className="textarea textarea-bordered" value={formData.conditions} onChange={handleChange} placeholder="e.g., Type 2 Diabetes, Hypertension" rows={2} />
                </div>
              </div>
            </div>

            {/* Vital Signs */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Vital Signs</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="form-control">
                  <label className="label"><span className="label-text">Blood Pressure</span></label>
                  <input type="text" name="bloodPressure" className="input input-bordered" value={formData.bloodPressure} onChange={handleChange} placeholder="e.g., 120/80" />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Heart Rate (bpm)</span></label>
                  <input type="number" name="heartRate" className="input input-bordered" value={formData.heartRate} onChange={handleChange} placeholder="e.g., 72" />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Temperature (°C)</span></label>
                  <input type="number" name="temperature" className="input input-bordered" value={formData.temperature} onChange={handleChange} placeholder="e.g., 37.2" step="0.1" />
                </div>
              </div>
            </div>

            {/* Record Information */}
            <div>
              <h3 className="font-semibold text-lg mb-3">Record Information</h3>
              <div className="form-control w-full md:w-1/3">
                <label className="label"><span className="label-text">Last Updated</span></label>
                <input type="date" name="lastUpdated" className="input input-bordered" value={formData.lastUpdated} onChange={handleChange} />
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full" disabled={loading}>
              {loading ? <span className="loading loading-spinner loading-sm"></span> : null}
              {loading ? 'Validating...' : 'Validate Data Quality'}
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
            <h2 className="card-title text-xl">Validation Result</h2>

            {/* Overall score — DaisyUI stat + badge */}
            <div className="stats shadow w-full mb-4">
              <div className="stat">
                <div className="stat-title">Overall Quality Score</div>
                <div className="stat-value">{Math.round(result.overall_score)}%</div>
                <div className="stat-desc mt-1">
                  <span className={`badge ${overall.badge}`}>{overall.label}</span>
                </div>
              </div>
            </div>

            {/* Quality dimensions — DaisyUI card + stat + progress */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              {['completeness', 'validity', 'consistency', 'timeliness'].map(dim => {
                const score = Math.round(result.breakdown[dim]);
                const style = SCORE_BADGE(score);
                return (
                  <div key={dim} className="card bg-base-200">
                    <div className="card-body p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium capitalize">{dim}</span>
                        <span className={`badge ${style.badge}`}>{score}%</span>
                      </div>
                      <progress className={`progress ${style.progress} w-full`} value={score} max="100"></progress>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Issues — DaisyUI alert per severity */}
            {result.issues_detected && result.issues_detected.length > 0 ? (
              <div>
                <h4 className="font-semibold mb-3">Issues Detected ({result.issues_detected.length})</h4>
                <div className="space-y-2">
                  {result.issues_detected.map((issue, idx) => {
                    const sev = issue.severity.toLowerCase();
                    return (
                      <div key={idx} className={`alert ${SEVERITY_ALERT[sev] || 'alert-ghost'} py-2`}>
                        <span className={`badge ${SEVERITY_BADGE[sev] || 'badge-ghost'} mr-2`}>{issue.severity.toUpperCase()}</span>
                        <span className="font-medium mr-1">{issue.field}:</span>
                        <span>{issue.issue}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="alert alert-success">
                <span>No data quality issues detected.</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ValidationForm;
