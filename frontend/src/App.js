import React, { useState } from 'react';
import ReconciliationForm from './components/ReconciliationForm';
import ValidationForm from './components/ValidationForm';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('reconciliation');

  return (
    <div className="app">
      <header className="app-header">
        <h1>Clinical Data Reconciliation Engine</h1>
        <p>AI-powered medication reconciliation and data quality validation</p>
      </header>

      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'reconciliation' ? 'active' : ''}`}
          onClick={() => setActiveTab('reconciliation')}
        >
          Medication Reconciliation
        </button>
        <button
          className={`tab-button ${activeTab === 'validation' ? 'active' : ''}`}
          onClick={() => setActiveTab('validation')}
        >
          Data Quality Validation
        </button>
      </div>

      <main className="app-main">
        {activeTab === 'reconciliation' && <ReconciliationForm />}
        {activeTab === 'validation' && <ValidationForm />}
      </main>

      <footer className="app-footer">
        <p>© 2024 Clinical Data Reconciliation Engine. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;
