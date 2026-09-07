# FHIR R5 Interoperability & HIPAA Security Rule

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## FHIR R5 (verified posture)

| Topic | Finding |
|-------|---------|
| US production exchange | **FHIR R4 + US Core** (US Core v9 still on R4 / USCDI) |
| US Core on R5 | **None** — HL7 path skips R5; R6 planned for future US Core |
| R5 value | Optional research interop; SubscriptionTopic model; additional resources |
| TMRDS default | `TMRDS_FHIR_VERSION=R4` via `FHIRR5Interop` |

Module: `engines/fhir_r5_interop.py` — capability statement + migration notes.  
Production maps remain US Core R4 (`fhir_us_core_mapper.py`).

## HIPAA Security Rule — technical safeguards (45 CFR 164.312)

| Standard | TMRDS control |
|----------|---------------|
| Access control — unique user ID (Required) | Session user_id |
| Emergency access (Required) | `emergency` break-glass account |
| Automatic logoff (Addressable) | Configurable session timeout (default 15 min) |
| Encryption (Addressable) | Deploy behind TLS; disk encryption operational |
| Audit controls | Append-only JSONL audit log |
| Integrity | HMAC integrity seal on clinical search payloads |
| Authentication | Password-authenticated sessions (replace defaults on deploy) |
| Transmission security | TLS at reverse proxy / load balancer |

Module: `engines/hipaa_security_controls.py`

**Note:** Technical controls alone do not equal full HIPAA compliance. Policies, BAAs, workforce training, and physical safeguards are organizational obligations.

## Doctor console

- UI: `frontend/` served by FastAPI at `/`
- API: `/api/v1/*`
- Deploy: `./deploy.sh` or `docker compose up`
