# TMRDS — Tucker Medical Research and Development System

**Research-advisory** clinical platform for Tri-State (IN / IL / KY) care and precision research.

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620  
**Not FDA-cleared SaMD.** Human authority remains final.

---

## Doctor console (start here)

```bash
pip install -r requirements.txt
chmod +x deploy.sh
./deploy.sh
# open http://localhost:8000
# sign in: clinician / change-me-on-deploy
```

Or: `docker compose up --build`

| Surface | Path |
|---------|------|
| Clinician UI | `/` (`frontend/`) |
| Health | `GET /health` |
| Login | `POST /api/v1/auth/login` |
| Clinical search | `POST /api/v1/clinical/search` |
| Live analytics | `GET /api/v1/analytics/live` |
| ICD-10 / RxNorm | `/api/v1/terminology/*` |
| Device (IEEE 11073) | `POST /api/v1/device/observation` |
| Audit log | `GET /api/v1/audit/recent` |

Default password **must** be changed before any real ePHI environment.

---

## Standards posture

| Topic | TMRDS |
|-------|-------|
| FHIR | **R4 US Core production**; R5 optional research (`FHIRR5Interop`) |
| HIPAA | Technical controls per **45 CFR 164.312** (session, audit, integrity HMAC, emergency access) |
| OMOP | CDM v5.4 + US Core concept map |
| Evidence | PubMed, ClinicalTrials.gov, NLM Clinical Tables (API-only) |

Docs: [MEDICAL_PROFESSIONAL_INSPECTION.md](docs/MEDICAL_PROFESSIONAL_INSPECTION.md) · [FHIR_R5_HIPAA.md](docs/FHIR_R5_HIPAA.md) · [ARCHITECTURE_VERIFICATION.md](docs/ARCHITECTURE_VERIFICATION.md)

---

## Removed / not claimed

Religious seals, street-address SSoT, unverified TPS/6G product claims, disease “cure” automation.

**Repo:** https://github.com/ATphobia22/TMRDS
