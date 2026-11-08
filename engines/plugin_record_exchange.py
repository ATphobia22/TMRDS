"""Read-only review of public metadata exported from research connectors."""
from __future__ import annotations
import hashlib
import json
from copy import deepcopy
from urllib.parse import urlsplit
from engines.biomedical_provider_registry import validate_research_record


def preview_records(records: list[dict]) -> dict:
    if not 1 <= len(records) <= 100:
        raise ValueError("supply 1-100 public research records")
    result, seen = [], set()
    for record in records:
        # Bound all fields before provenance validation; no URL is fetched.
        if len(json.dumps(record)) > 12000:
            raise ValueError("research metadata record too large")
        checked = validate_research_record(deepcopy(record))
        if checked['provider_id'] == 'health':
            raise ValueError("personal health records cannot enter public research exchange")
        url = urlsplit(checked['source_url'])
        if url.query or url.fragment:
            raise ValueError("source URLs must omit query strings and fragments")
        identity = (checked['provider_id'], checked['source_id'])
        if identity in seen:
            raise ValueError("duplicate provider/source identity")
        seen.add(identity)
        checked['record_sha256'] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        checked['hash_scope'] = 'submitted_metadata'
        result.append(checked)
    return {'status':'UNREVIEWED_IMPORT_PREVIEW','persisted':False,'network_requests_made':False,
            'source_truth_verified':False,'clinical_promotion_allowed':False,'records':result}
