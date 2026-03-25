import React, { useState } from 'react';
import './ReconciliationForm.css';

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
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSourceChange = (index, field, value) => {
    const newSources = [...formData.sources];
    newSources[index][field] = value;
    setFormData(prev => ({
      ...prev,
      sources: newSources
    }));
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
              value: {
                text_value: parts[1] || null,
                numeric_value: null,
                unit: parts[2] || null
              }
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

      const response = await fetch('http://localhost:8000/api/reconcile/medication', {
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

  return (
    <div className="form-container">
      <div className="form-section">
        <h2>Medication Reconciliation</h2>
        <p className="form-description">
          Enter patient information and medication sources from different systems for reconciliation.
        </p>

        <form onSubmit={handleSubmit} className="reconciliation-form">
          <div className="form-group patient-info">
            <h3>Patient Information</h3>
            
            <div className="input-row">
              <div className="input-field">
                <label htmlFor="age">Age</label>
                <input
                  type="number"
                  id="age"
                  name="age"
                  value={formData.age}
                  onChange={handleFieldChange}
                  placeholder="e.g., 45"
                />
              </div>

              <div className="input-field">
                <label htmlFor="conditions">Conditions</label>
                <input
                  type="text"
                  id="conditions"
                  name="conditions"
                  value={formData.conditions}
                  onChange={handleFieldChange}
                  placeholder="e.g., Hypertension, Type 2 Diabetes"
                />
              </div>
            </div>

            <div className="input-field">
              <label htmlFor="recentLabs">Recent Labs (format: name:value:unit)</label>
              <textarea
                id="recentLabs"
                name="recentLabs"
                value={formData.recentLabs}
                onChange={handleFieldChange}
                placeholder="e.g., HbA1c:7.2:%, BP:120/80:mmHg"
                rows="3"
              />
            </div>
          </div>

          <div className="form-group sources-info">
            <h3>Medication Sources</h3>
            
            {formData.sources.map((source, index) => (
              <div key={index} className="source-card">
                <div className="source-header">
                  <h4>Source {index + 1}</h4>
                  {formData.sources.length > 1 && (
                    <button
                      type="button"
                      className="remove-btn"
                      onClick={() => removeSource(index)}
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="input-row">
                  <div className="input-field">
                    <label>System</label>
                    <input
                      type="text"
                      value={source.system}
                      onChange={(e) => handleSourceChange(index, 'system', e.target.value)}
                      placeholder="e.g., Hospital EMR, Pharmacy System"
                    />
                  </div>

                  <div className="input-field">
                    <label>Medication</label>
                    <input
                      type="text"
                      value={source.medication}
                      onChange={(e) => handleSourceChange(index, 'medication', e.target.value)}
                      placeholder="e.g., Metformin 500mg"
                    />
                  </div>
                </div>

                <div className="input-row">
                  <div className="input-field">
                    <label>Last Updated</label>
                    <input
                      type="date"
                      value={source.lastUpdated}
                      onChange={(e) => handleSourceChange(index, 'lastUpdated', e.target.value)}
                    />
                  </div>

                  <div className="input-field">
                    <label>Reliability</label>
                    <select
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
            ))}

            <button type="button" className="add-source-btn" onClick={addSource}>
              + Add Another Source
            </button>
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Reconciling...' : 'Reconcile Medication'}
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
          <h2>Reconciliation Result</h2>
          
          <div className="result-card">
            <div className="result-header">
              <h3>{result.reconciled_medication || 'Unknown'}</h3>
              <div className="confidence-badge" style={{
                backgroundColor: result.confidence_score > 0.75 ? '#48bb78' : 
                               result.confidence_score > 0.5 ? '#ed8936' : '#f56565'
              }}>
                {Math.round(result.confidence_score * 100)}% Confidence
              </div>
            </div>

            <div className="result-row">
              <div className="result-item">
                <h4>Safety Check</h4>
                <p className={`safety-${result.clinical_safety_check.toLowerCase()}`}>
                  {result.clinical_safety_check}
                </p>
              </div>
            </div>

            <div className="result-row">
              <div className="result-item">
                <h4>Reasoning</h4>
                <p>{result.reasoning}</p>
              </div>
            </div>

            {result.recommended_actions && result.recommended_actions.length > 0 && (
              <div className="result-row">
                <div className="result-item">
                  <h4>Recommended Actions</h4>
                  <ul>
                    {result.recommended_actions.map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ReconciliationForm;
