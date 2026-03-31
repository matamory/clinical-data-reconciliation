import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app

client = TestClient(app)


class TestReconciliationAPI:
    """Test suite for medication reconciliation endpoint."""
    
    def test_healthy_endpoint(self):
        """Test 1: Health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_reconcile_single_medication_source(self):
        """Test 2: Reconcile medication from single high-reliability source."""
        payload = {
            "patient_context": {
                "age": 45,
                "conditions": ["Hypertension", "Type 2 Diabetes"],
                "recent_labs": [
                    {"name": "HbA1c", "value": {"numeric_value": 7.2, "text_value": None, "unit": "%"}},
                    {"name": "BP", "value": {"numeric_value": 130, "text_value": None, "unit": "mmHg"}}
                ]
            },
            "sources": [
                {
                    "system": "Hospital EMR",
                    "medication": "Metformin 500mg",
                    "last_updated": "2024-03-20",
                    "last_filled": None,
                    "source_reliability": "high"
                }
            ]
        }
        
        response = client.post("/api/reconcile/medication", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["reconciled_medication"] == "Metformin 500mg"
        assert data["confidence_score"] > 0.5
        assert data["clinical_safety_check"] in ["PASSED", "FAILED", "REVIEW_REQUIRED"]
        assert len(data["recommended_actions"]) > 0
    
    def test_reconcile_conflicting_medications(self):
        """Test 3: Reconcile conflicting medications from multiple sources."""
        payload = {
            "patient_context": {
                "age": 65,
                "conditions": ["Hypertension", "Heart Disease"],
                "recent_labs": []
            },
            "sources": [
                {
                    "system": "Hospital EMR",
                    "medication": "Lisinopril 10mg",
                    "last_updated": "2024-03-20",
                    "last_filled": None,
                    "source_reliability": "high"
                },
                {
                    "system": "Pharmacy System",
                    "medication": "Enalapril 10mg",
                    "last_updated": "2024-03-15",
                    "last_filled": None,
                    "source_reliability": "medium"
                }
            ]
        }
        
        response = client.post("/api/reconcile/medication", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should reconcile to one
        assert data["reconciled_medication"] is not None
        assert data["confidence_score"] >= 0
        assert data["clinical_safety_check"] in ["PASSED", "FAILED", "REVIEW_REQUIRED"]
        # Should flag uncertainty
        assert len(data["recommended_actions"]) > 0
    
    def test_reconcile_with_recent_vs_old_data(self):
        """Test 4: High reliability and recency scores for recent data."""
        payload = {
            "patient_context": {
                "age": 50,
                "conditions": ["Diabetes"],
                "recent_labs": []
            },
            "sources": [
                {
                    "system": "Primary Care",
                    "medication": "Insulin Glargine",
                    "last_updated": "2024-03-24",  # Very recent
                    "last_filled": None,
                    "source_reliability": "high"
                }
            ]
        }
        
        response = client.post("/api/reconcile/medication", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["reconciled_medication"] == "Insulin Glargine"
        # Recent + high reliability = high confidence
        assert data["confidence_score"] > 0.65
    
    def test_reconcile_no_sources_error_handling(self):
        """Test 5: Graceful handling when no medication sources provided."""
        payload = {
            "patient_context": {
                "age": 30,
                "conditions": [],
                "recent_labs": []
            },
            "sources": []
        }
        
        response = client.post("/api/reconcile/medication", json=payload)
        assert response.status_code == 422
        data = response.json()

        # Should return a 422 error with a detail message
        assert "detail" in data

    def test_reconcile_prefers_recent_renal_appropriate_metformin(self):
        """Select more recent, renal-appropriate metformin dose when eGFR is reduced."""
        payload = {
            "patient_context": {
                "age": 67,
                "conditions": ["Type 2 Diabetes", "Hypertension"],
                "recent_labs": [
                    {
                        "name": "eGFR",
                        "value": {
                            "numeric_value": 45,
                            "text_value": None,
                            "unit": "mL/min/1.73m2"
                        }
                    }
                ]
            },
            "sources": [
                {
                    "system": "Hospital EHR",
                    "medication": "Metformin 1000mg twice daily",
                    "last_updated": "2024-10-15",
                    "last_filled": None,
                    "source_reliability": "high"
                },
                {
                    "system": "Primary Care",
                    "medication": "Metformin 500mg twice daily",
                    "last_updated": "2025-01-20",
                    "last_filled": None,
                    "source_reliability": "high"
                },
                {
                    "system": "Pharmacy",
                    "medication": "Metformin 1000mg daily",
                    "last_updated": None,
                    "last_filled": "2025-01-25",
                    "source_reliability": "medium"
                }
            ]
        }

        response = client.post("/api/reconcile/medication", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["reconciled_medication"] == "Metformin 500mg twice daily"
        assert data["confidence_score"] >= 0.75
        assert "most recent clinical encounter" in data["reasoning"].lower()
        assert "dose reduction appropriate" in data["reasoning"].lower()
        assert "pharmacy fill may reflect old prescription" in data["reasoning"].lower()
        assert data["recommended_actions"] == [
            "Update Hospital EHR to Metformin 500mg twice daily",
            "Verify with pharmacist that correct dose is being filled"
        ]


class TestValidationAPI:
    """Test suite for data quality validation endpoint."""
    
    def test_validate_complete_data(self):
        """Test complete patient data with all fields populated."""
        payload = {
            "demographics": {
                "name": "John Doe",
                "dob": "1975-05-15",
                "gender": "male"
            },
            "medications": ["Metformin 500mg", "Lisinopril 10mg"],
            "allergies": ["Penicillin"],
            "conditions": ["Type 2 Diabetes", "Hypertension"],
            "vital_signs": {
                "blood_pressure": "130/80",
                "heart_rate": 72,
                "temperature": 37.2,
                "respiratory_rate": None
            },
            "last_updated": "2024-03-24"
        }
        
        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "overall_score" in data
        assert data["overall_score"] > 70  # Should be good score
        assert "breakdown" in data
        assert "completeness" in data["breakdown"]
        assert "validity" in data["breakdown"]
        assert "consistency" in data["breakdown"]
        assert "timeliness" in data["breakdown"]
    
    def test_validate_incomplete_data(self):
        """Test incomplete patient data with missing required fields."""
        payload = {
            "demographics": {
                "name": "",  # Missing name
                "dob": None,
                "gender": None
            },
            "medications": [],
            "allergies": [],
            "conditions": [],
            "vital_signs": None,  # Missing vitals
            "last_updated": None
        }
        
        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should detect issues
        assert data["overall_score"] < 50  # Should be poor
        assert len(data["issues_detected"]) > 0
        
        # Should have high-severity issues
        high_severity = [i for i in data["issues_detected"] if i["severity"] == "high"]
        assert len(high_severity) > 0
    
    def test_validate_invalid_data_formats(self):
        """Test validation with invalid data formats."""
        payload = {
            "demographics": {
                "name": "Jane Doe",
                "dob": "2025-12-25",  # Future date
                "gender": "invalid_gender"
            },
            "medications": [],
            "allergies": [],
            "conditions": [],
            "vital_signs": {
                "blood_pressure": "120/80",
                "heart_rate": 300,  # Invalid HR
                "temperature": 50,  # Fever too high
                "respiratory_rate": None
            },
            "last_updated": "2024-03-24"
        }
        
        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should detect validity issues
        validity_issues = [i for i in data["issues_detected"] 
                          if "dob" in i["field"] or "heart_rate" in i["field"] or "temperature" in i["field"]]
        assert len(validity_issues) > 0
    
    def test_validate_stale_data(self):
        """Test validation with very old/stale data."""
        payload = {
            "demographics": {
                "name": "Robert Smith",
                "dob": "1970-01-01",
                "gender": "male"
            },
            "medications": ["Aspirin 81mg"],
            "allergies": [],
            "conditions": ["Heart Disease"],
            "vital_signs": {
                "blood_pressure": "140/90",
                "heart_rate": 75,
                "temperature": None,
                "respiratory_rate": None
            },
            "last_updated": "2023-01-01"  # Over 1 year old
        }
        
        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Timeliness should be poor
        assert data["breakdown"]["timeliness"] < 50
        
        # Should have timeliness-related issues
        timeliness_issues = [i for i in data["issues_detected"] if "last_updated" in i["field"]]
        assert len(timeliness_issues) > 0

    def test_validate_missing_allergies_reduces_completeness(self):
        """Missing allergy documentation should reduce completeness and create an issue."""
        payload = {
            "demographics": {
                "name": "John Doe",
                "dob": "1975-05-15",
                "gender": "male"
            },
            "medications": ["Metformin 500mg", "Lisinopril 10mg"],
            "allergies": [],
            "conditions": ["Type 2 Diabetes", "Hypertension"],
            "vital_signs": {
                "blood_pressure": "130/80",
                "heart_rate": 72,
                "temperature": 37.2,
                "respiratory_rate": None
            },
            "last_updated": "2024-03-24"
        }

        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["breakdown"]["completeness"] <= 85
        allergy_issues = [i for i in data["issues_detected"] if i["field"] == "allergies"]
        assert len(allergy_issues) > 0

    def test_validate_implausible_bp_reduces_validity(self):
        """Clinically implausible blood pressure should reduce validity and create an issue."""
        payload = {
            "demographics": {
                "name": "John Doe",
                "dob": "1975-05-15",
                "gender": "male"
            },
            "medications": ["Metformin 500mg", "Lisinopril 10mg"],
            "allergies": ["Penicillin"],
            "conditions": ["Type 2 Diabetes", "Hypertension"],
            "vital_signs": {
                "blood_pressure": "340/180",
                "heart_rate": 72,
                "temperature": 37.2,
                "respiratory_rate": None
            },
            "last_updated": "2024-03-24"
        }

        response = client.post("/api/validate/data-quality", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["breakdown"]["validity"] <= 80
        bp_issues = [i for i in data["issues_detected"] if i["field"] == "vital_signs.blood_pressure"]
        assert len(bp_issues) > 0


class TestAPIIntegration:
    """Integration tests for full workflow."""
    
    def test_root_endpoint(self):
        """Test root endpoint for basic connectivity."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
    
    def test_full_workflow(self):
        """Test complete workflow: validate data then reconcile medications."""
        # First validate data
        validation_payload = {
            "demographics": {
                "name": "Alice Johnson",
                "dob": "1980-07-22",
                "gender": "female"
            },
            "medications": ["Atorvastatin 20mg"],
            "allergies": [],
            "conditions": ["High Cholesterol"],
            "vital_signs": {
                "blood_pressure": "118/76",
                "heart_rate": 68,
                "temperature": None,
                "respiratory_rate": None
            },
            "last_updated": "2024-03-24"
        }
        
        val_response = client.post("/api/validate/data-quality", json=validation_payload)
        assert val_response.status_code == 200
        val_data = val_response.json()
        
        # Data should be valid
        assert val_data["overall_score"] > 60
        
        # Then reconcile medications
        recon_payload = {
            "patient_context": {
                "age": 44,
                "conditions": ["High Cholesterol"],
                "recent_labs": []
            },
            "sources": [
                {
                    "system": "Primary Care",
                    "medication": "Atorvastatin 20mg",
                    "last_updated": "2024-03-24",
                    "last_filled": None,
                    "source_reliability": "high"
                }
            ]
        }
        
        recon_response = client.post("/api/reconcile/medication", json=recon_payload)
        assert recon_response.status_code == 200
        recon_data = recon_response.json()
        
        # Should reconcile with high confidence
        assert recon_data["reconciled_medication"] == "Atorvastatin 20mg"
        assert recon_data["confidence_score"] > 0.6


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
