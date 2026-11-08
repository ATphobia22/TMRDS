"""Explicit human label submission to a local MONAILabel research server."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from engines.imaging_transport import ImagingSession
from engines.research_dicomweb import ResearchDICOMweb


class HumanAnnotationClient:
    def __init__(self, base_url="http://127.0.0.1:8000", *, local_sandbox=True, auth=None):
        self.session = ImagingSession(base_url, local_sandbox=local_sandbox, methods=("GET", "PUT"), max_bytes=1024 * 1024)
        self.session.auth = auth
        self.base_url = base_url.rstrip("/")

    def info(self):
        return self.session.get(self.base_url + "/info/").json()

    def submit(self, *, image_id: str, label: Path, reviewer: str, source_uids: dict, confirmed: bool):
        if confirmed is not True or not reviewer.strip() or not image_id.strip() or len(image_id) > 256:
            raise ValueError("explicit human confirmation, reviewer and image id required")
        if set(source_uids) != {"study", "series", "instance"}:
            raise ValueError("all source UIDs required")
        for uid in source_uids.values():
            ResearchDICOMweb._uid(uid)
        if label.suffix not in {".nrrd", ".nii", ".gz", ".dcm"} or label.is_symlink():
            raise ValueError("unsupported label file")
        with label.open("rb") as stream:
            data = stream.read(10 * 1024 * 1024 + 1)
        if not data or len(data) > 10 * 1024 * 1024:
            raise ValueError("annotation exceeds byte budget or is empty")
        evidence = {"reviewer": reviewer, "source_uids": source_uids,
                    "label_sha256": hashlib.sha256(data).hexdigest(), "state": "human_submitted",
                    "clinical_approval": False}
        # MONAILabel 0.8.5 client.save_label contract: PUT, image/tag query,
        # multipart label file and JSON params field. No automatic write retries.
        response = self.session.put(self.base_url + "/datastore/label",
            params={"image": image_id, "tag": "tmrds-human"},
            data={"params": json.dumps({"tmrds": evidence})},
            files={"label": (label.name, data, "application/octet-stream")})
        return {"evidence": evidence, "upstream": response.json()}

    def close(self):
        self.session.close()
