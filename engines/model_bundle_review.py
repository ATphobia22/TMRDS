"""Review local MONAI weights before loading; never execute bundle configuration."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path

ALLOWED_LICENSES = {"Apache-2.0", "MIT", "BSD-3-Clause", "BSD-2-Clause", "CC-BY-4.0", "CC0-1.0"}
MAX_WEIGHTS_BYTES = 512 * 1024 * 1024


def review_bundle(directory: Path, manifest: dict) -> dict:
    if manifest.get("license") not in ALLOWED_LICENSES:
        raise ValueError("license requires review or is unsupported")
    reviewer = manifest.get("reviewer")
    if manifest.get("intended_use") != "research" or not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("research use and named human reviewer required")
    if manifest.get("license_reviewed") is not True or manifest.get("model_card_reviewed") is not True:
        raise ValueError("license and model card review attestations required")
    root = Path(directory).resolve()
    files = manifest.get("files", {})
    if not files or not all(k in files for k in (manifest.get("weights"), manifest.get("license_file"), manifest.get("model_card"))):
        raise ValueError("weights, license text and model card checksums required")
    verified = {}
    for name, digest in files.items():
        path = root / name
        if Path(name).is_absolute() or ".." in Path(name).parts or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("unsafe bundle path")
        if not path.is_file() or not path.resolve().is_relative_to(root) or path.stat().st_size > MAX_WEIGHTS_BYTES:
            raise ValueError("missing or oversized bundle artifact")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError("bundle checksum mismatch")
        verified[name] = actual
    return {"state": "research_reviewed", "reviewer": manifest["reviewer"], "files": verified,
            "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "clinical_validation": "not_established", "license": manifest["license"]}


def load_reviewed_weights(directory: Path, manifest: dict):
    """Only CPU tensor checkpoints; config scripts, TorchScript and full objects disallowed."""
    review_bundle(directory, manifest)
    # Load the checked bytes, avoiding a path replacement between check and torch.load.
    data = (Path(directory) / manifest["weights"]).read_bytes()
    if len(data) > MAX_WEIGHTS_BYTES or hashlib.sha256(data).hexdigest() != manifest["files"][manifest["weights"]]:
        raise ValueError("weights changed after review")
    import torch
    result = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
    if not isinstance(result, dict) or not all(isinstance(k, str) and isinstance(v, torch.Tensor) for k, v in result.items()):
        raise ValueError("only a tensor state dictionary is supported")
    return result
