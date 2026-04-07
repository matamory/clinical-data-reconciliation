// Governing: SPEC-0001 REQ "React Frontend with Tailwind CSS", SPEC-0001 REQ "DaisyUI Component Integration"
import React, { useState } from 'react';
import ReconciliationForm from './components/ReconciliationForm';
import ValidationForm from './components/ValidationForm';

function App() {
  const [activeTab, setActiveTab] = useState('reconciliation');

  return (
    <div className="min-h-screen bg-base-200">
      <header className="bg-primary text-primary-content shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Clinical Data Reconciliation Engine</h1>
          <p className="text-sm opacity-75">AI-powered medication reconciliation and data quality validation</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <div className="tabs tabs-boxed bg-base-100 mb-6 w-fit">
          <button
            className={`tab ${activeTab === 'reconciliation' ? 'tab-active' : ''}`}
            onClick={() => setActiveTab('reconciliation')}
          >
            Medication Reconciliation
          </button>
          <button
            className={`tab ${activeTab === 'validation' ? 'tab-active' : ''}`}
            onClick={() => setActiveTab('validation')}
          >
            Data Quality Validation
          </button>
        </div>

        {activeTab === 'reconciliation' ? <ReconciliationForm /> : <ValidationForm />}
      </main>

      <footer className="footer footer-center p-4 bg-base-300 text-base-content mt-8">
        <p className="text-sm">Clinical Data Reconciliation Engine — For clinical use only</p>
      </footer>
    </div>
  );
}

export default App;
