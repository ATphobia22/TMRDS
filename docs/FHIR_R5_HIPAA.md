# FHIR R5 Interoperability & HIPAA Security Rule

## FHIR R5 (verified posture)

| Topic | Finding |
|-------|---------|
| US production exchange | **FHIR R4 + US Core** |
| US Core on R5 | Research interoperability only; do not imply US Core R5 production support |
| R5 value | Optional research interop; SubscriptionTopic model; additional resources |
| TMRDS default | `TMRDS_FHIR_VERSION=R4` via `FHIRR5Interop` |

Module: `engines/fhir_r5_interop.py` — capability statement + migration notes.  
Production maps remain US Core R4 (`fhir_us_core_mapper.py`).

## HIPAA Security Rule — technical safeguards (45 CFR 164.312)

| Standard | TMRDS control |
|----------|---------------|
| Access control — unique user ID (Required) | Session user_id |
| Emergency access (Required) | Configured `emergency` break-glass account; no built-in PIN |
| Automatic logoff (Addressable) | Configurable session timeout (default 15 min) |
| Encryption (Addressable) | Deploy behind TLS; disk encryption operational |
| Audit controls | Append-only JSONL audit log |
| Integrity | HMAC integrity seal on clinical search payloads |
| Authentication | Environment/secret-manager supplied credentials; salted PBKDF2-HMAC-SHA256 password verification |
| Transmission security | TLS at reverse proxy / load balancer |

Module: `engines/hipaa_security_controls.py`

**Security requirement:** Production deployments require `TMRDS_HMAC_SECRET`, `TMRDS_CLINICIAN_PASSWORD`, and `TMRDS_EMERGENCY_PIN`; no development credential fallback is permitted.

**Note:** Technical controls alone do not equal full HIPAA compliance. Policies, BAAs, workforce training, and physical safeguards are organizational obligations.

## Doctor console

- UI: `frontend/` served by FastAPI at `/`
- API: `/api/v1/*`
- Deploy: `./deploy.sh` or `docker compose up`
