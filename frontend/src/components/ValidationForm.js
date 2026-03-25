import React, { useState } from 'react';
import './ValidationForm.css';

function ValidationForm() {
  const [formData, setFormData] = useState({
    name: '',
    dob: '',
    gender: '',
    medications: '',
    allergies: '',
    conditions: '',
    bloodPressure: '',
    heartRate: '',
    temperature: '',
    lastUpdated: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
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

      const response = await fetch('http://localhost:8000/api/validate/data-quality', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#48bb78';
    if (score >= 75) return '#38b6ff';
    if (score >= 60) return '#ed8936';
    if (score >= 40) return '#f6ad55';
    return '#f56565';
  };

  const getScoreStatus = (score) => {
    if (score >= 90) return 'EXCELLENT';
    if (score >= 75) return 'GOOD';
    if (score >= 60) return 'ACCEPTABLE';
    if (score >= 40) return 'POOR';
    return 'CRITICAL';
  };

  return (
    <div className="validation-container">
      <div className="validation-section">
        <h2>Data Quality Validation</h2>
        <p className="form-description">
          Validate patient data quality across four dimensions: completeness, validity, consistency, and timeliness.
        </p>

        <form onSubmit={handleSubmit} className="validation-form">
          <div className="form-group demographics-info">
            <h3>Demographics</h3>
            
            <div className="input-row">
              <div className="input-field">
                <label htmlFor="name">Patient Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., John Doe"
                />
              </div>

              <div className="input-field">
                <label htmlFor="dob">Date of Birth</label>
                <input
                  type="date"
                  id="dob"
                  name="dob"
                  value={formData.dob}
                  onChange={handleChange}
                />
              </div>

              <div className="input-field">
                <label htmlFor="gender">Gender</label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                >
                  <option value="">Select...</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>
            </div>
          </div>

          <div className="form-group clinical-info">
            <h3>Clinical Information</h3>
            
            <div className="input-field">
              <label htmlFor="medications">Medications (comma-separated)</label>
              <textarea
                id="medications"
                name="medications"
                value={formData.medications}
                onChange={handleChange}
                placeholder="e.g., Metformin 500mg, Lisinopril 10mg"
                rows="2"
              />
            </div>

            <div className="input-field">
              <label htmlFor="allergies">Allergies (comma-separated)</label>
              <textarea
                id="allergies"
                name="allergies"
                value={formData.allergies}
                onChange={handleChange}
                placeholder="e.g., Penicillin, Shellfish"
                rows="2"
              />
            </div>

            <div className="input-field">
              <label htmlFor="conditions">Medical Conditions (comma-separated)</label>
              <textarea
                id="conditions"
                name="conditions"
                value={formData.conditions}
                onChange={handleChange}
                placeholder="e.g., Type 2 Diabetes, Hypertension"
                rows="2"
              />
            </div>
          </div>

          <div className="form-group vitals-info">
            <h3>Vital Signs</h3>
            
            <div className="input-row">
              <div className="input-field">
                <label htmlFor="bloodPressure">Blood Pressure</label>
                <input
                  type="text"
                  id="bloodPressure"
                  name="bloodPressure"
                  value={formData.bloodPressure}
                  onChange={handleChange}
                  placeholder="e.g., 120/80"
                />
              </div>

              <div className="input-field">
                <label htmlFor="heartRate">Heart Rate (bpm)</label>
                <input
                  type="number"
                  id="heartRate"
                  name="heartRate"
                  value={formData.heartRate}
                  onChange={handleChange}
                  placeholder="e.g., 72"
                />
              </div>

              <div className="input-field">
                <label htmlFor="temperature">Temperature (°C)</label>
                <input
                  type="number"
                  id="temperature"
                  name="temperature"
                  value={formData.temperature}
                  onChange={handleChange}
                  placeholder="e.g., 37.2"
                  step="0.1"
                />
              </div>
            </div>
          </div>

          <div className="form-group meta-info">
            <h3>Record Information</h3>
            
            <div className="input-field">
              <label htmlFor="lastUpdated">Last Updated</label>
              <input
                type="date"
                id="lastUpdated"
                name="lastUpdated"
                value={formData.lastUpdated}
                onChange={handleChange}
              />
            </div>
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Validating...' : 'Validate Data Quality'}
          </button>
        </form>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="result-section">
          <h2>Validation Result</h2>
          
          <div className="overall-score" style={{
            borderTopColor: getScoreColor(result.overall_score)
          }}>
            <div className="score-display">
              <div className="score-number" style={{
                color: getScoreColor(result.overall_score)
              }}>
                {Math.round(result.overall_score)}%
              </div>
              <div className="score-status">
                {getScoreStatus(result.overall_score)}
              </div>
            </div>
          </div>

          <div className="breakdown-grid">
            <div className="breakdown-card">
              <h4>Completeness</h4>
              <div className="score-bar">
                <div className="score-fill" style={{
                  width: `${result.breakdown.completeness}%`,
                  backgroundColor: getScoreColor(result.breakdown.completeness)
                }}></div>
              </div>
              <p>{Math.round(result.breakdown.completeness)}%</p>
            </div>

            <div className="breakdown-card">
              <h4>Validity</h4>
              <div className="score-bar">
                <div className="score-fill" style={{
                  width: `${result.breakdown.validity}%`,
                  backgroundColor: getScoreColor(result.breakdown.validity)
                }}></div>
              </div>
              <p>{Math.round(result.breakdown.validity)}%</p>
            </div>

            <div className="breakdown-card">
              <h4>Consistency</h4>
              <div className="score-bar">
                <div className="score-fill" style={{
                  width: `${result.breakdown.consistency}%`,
                  backgroundColor: getScoreColor(result.breakdown.consistency)
                }}></div>
              </div>
              <p>{Math.round(result.breakdown.consistency)}%</p>
            </div>

            <div className="breakdown-card">
              <h4>Timeliness</h4>
              <div className="score-bar">
                <div className="score-fill" style={{
                  width: `${result.breakdown.timeliness}%`,
                  backgroundColor: getScoreColor(result.breakdown.timeliness)
                }}></div>
              </div>
              <p>{Math.round(result.breakdown.timeliness)}%</p>
            </div>
          </div>

          {result.issues_detected && result.issues_detected.length > 0 && (
            <div className="issues-section">
              <h3>Issues Detected ({result.issues_detected.length})</h3>
              <div className="issues-list">
                {result.issues_detected.map((issue, idx) => (
                  <div key={idx} className={`issue-card severity-${issue.severity.toLowerCase()}`}>
                    <div className="issue-header">
                      <span className={`severity-badge severity-${issue.severity.toLowerCase()}`}>
                        {issue.severity.toUpperCase()}
                      </span>
                      <span className="field-name">{issue.field}</span>
                    </div>
                    <p>{issue.issue}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!result.issues_detected || result.issues_detected.length === 0) && (
            <div className="success-message">
              ✓ No data quality issues detected!
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ValidationForm;
