import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
import requests
from engines.imaging_transport import ImagingSession
from engines.model_bundle_review import review_bundle, load_reviewed_weights
from engines.human_annotation import HumanAnnotationClient


def checkpoint(tmp_path):
    for name in ('weights.pt', 'LICENSE', 'model-card.md'):
        (tmp_path / name).write_bytes(b'research fixture')
    return {'license': 'MIT', 'intended_use': 'research', 'reviewer': 'human-fixture',
        'license_reviewed': True, 'model_card_reviewed': True,
        'weights': 'weights.pt', 'license_file': 'LICENSE', 'model_card': 'model-card.md',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()}}


def test_review_refuses_tampering_missing_review_and_paths(tmp_path):
    manifest = checkpoint(tmp_path)
    assert review_bundle(tmp_path, manifest)['state'] == 'research_reviewed'
    for delta in ({'license': 'unknown'}, {'reviewer': ''}, {'reviewer': None}, {'model_card_reviewed': False},
                  {'files': {'../outside': 'abc'}}):
        with pytest.raises(ValueError):
            review_bundle(tmp_path, {**manifest, **delta})
    (tmp_path / 'weights.pt').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='checksum'):
        load_reviewed_weights(tmp_path, manifest)


def test_load_only_tensor_state_after_review(tmp_path):
    torch = pytest.importorskip('torch')
    manifest = checkpoint(tmp_path)
    torch.save({'weight': torch.ones(1)}, tmp_path / 'weights.pt')
    manifest['files']['weights.pt'] = hashlib.sha256((tmp_path / 'weights.pt').read_bytes()).hexdigest()
    assert load_reviewed_weights(tmp_path, manifest)['weight'].item() == 1
    (tmp_path / 'LICENSE').unlink()
    with pytest.raises(ValueError):
        load_reviewed_weights(tmp_path, manifest)


def test_no_network_for_invalid_urls_and_methods():
    with pytest.raises(ValueError):
        ImagingSession('http://127.0.0.1:9999', local_sandbox=True)
    with pytest.raises(ValueError):
        ImagingSession('http://example.com')
    session = ImagingSession('http://127.0.0.1:8042/dicom-web', local_sandbox=True)
    for method, url in [('POST', session.base_url), ('GET', 'http://127.0.0.1:8042/system'),
                        ('GET', session.base_url + '/../system'), ('GET', 'http://evil.invalid/dicom-web')]:
        with pytest.raises(ValueError):
            session.request(method, url)


def response(status=200, content=b'[]'):
    result = requests.Response()
    result.status_code = status
    result.raw = __import__('io').BytesIO(content)
    result.headers['Content-Type'] = 'application/dicom+json'
    return result


def test_byte_cap_redirects_and_transport_options():
    session = ImagingSession('http://127.0.0.1:8042/dicom-web', local_sandbox=True, max_bytes=2)
    for result in (response(302), response(content=b'123')):
        with patch.object(requests.Session, 'request', return_value=result) as send:
            with pytest.raises(ValueError):
                session.get(session.base_url)
            kwargs = send.call_args.kwargs
            assert kwargs['allow_redirects'] is False and kwargs['timeout'] == (5, 10)
            assert kwargs['stream'] is True and session.trust_env is False


def test_real_dicomweb_library_uses_bounded_session():
    pytest.importorskip('dicomweb_client')
    from engines.research_dicomweb import ResearchDICOMweb
    client = ResearchDICOMweb('http://127.0.0.1:8042/dicom-web', local_sandbox=True)
    with patch.object(requests.Session, 'request', return_value=response(content=b'[{"0020000D":{"Value":["1.2.3"]}}]')) as send:
        assert client.studies(study_uid='1.2.3', limit=1)[0]['0020000D']['Value'] == ['1.2.3']
        assert 'limit=1' in send.call_args.args[1]
        assert client._client._max_attempts == 1
    with pytest.raises(ValueError):
        client.metadata('../bad', '1.2.3', '1.2.4')
    client.close()


def test_annotation_confirmation_and_exact_monailabel_contract(tmp_path):
    label = tmp_path / 'label.nrrd'
    label.write_bytes(b'NRRD0005\nfixture')
    client = HumanAnnotationClient()
    args = dict(image_id='image id', label=label, reviewer='reviewer',
                source_uids={'study': '1.2.3', 'series': '1.2.4', 'instance': '1.2.5'})
    with pytest.raises(ValueError):
        client.submit(**args, confirmed=False)
    with patch.object(requests.Session, 'request', return_value=response(content=b'{"label":"stored-label"}')) as send:
        result = client.submit(**args, confirmed=True)
        assert send.call_count == 1
        assert send.call_args.args == ('PUT', 'http://127.0.0.1:8000/datastore/label')
        assert send.call_args.kwargs['params'] == {'image': 'image id', 'tag': 'tmrds-human'}
        assert json.loads(send.call_args.kwargs['data']['params'])['tmrds']['clinical_approval'] is False
        assert result['evidence']['label_sha256'] == hashlib.sha256(label.read_bytes()).hexdigest()
    client.close()


def test_static_export_has_local_pixel_data_and_no_archive_password(tmp_path):
    pytest.importorskip('pydicom')
    from scripts.imaging_static_export import export_synthetic
    directory = tmp_path / 'offline'
    result = export_synthetic(directory)
    assert not (directory / 'orthanc.json').exists()
    for name, digest in result['artifacts'].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    study = json.loads((directory / 'ohif-dicom.json').read_text())['studies'][0]
    instance = study['series'][0]['instances'][0]
    assert instance['url'] == 'dicomweb:http://127.0.0.1:8080/synthetic-mr.dcm'
    assert instance['metadata']['Rows'] == 16
    assert result['evaluation']['browser_render_verified'] is False
    with pytest.raises(FileExistsError):
        export_synthetic(directory)


def test_existing_medicalnet_cannot_bypass_bundle_gate():
    pytest.importorskip('torch')
    pytest.importorskip('monai')
    from engines.medicalnet_backbone import MedicalNetBackbone
    with pytest.raises(ValueError, match='reviewed local bundle'):
        MedicalNetBackbone(depth=10, pretrained=True)
    net = MedicalNetBackbone(depth=10, pretrained=False)
    assert net.transfer_status()['status'] == 'UNTRAINED_RESEARCH'
    with pytest.raises(ValueError, match='reviewed bundle'):
        net.load_weights_manual('/tmp/unreviewed.pt')


def test_bundle_symlink_is_refused(tmp_path):
    manifest = checkpoint(tmp_path)
    original = (tmp_path / 'weights.pt').read_bytes()
    (tmp_path / 'weights.pt').unlink()
    outside = tmp_path.parent / 'outside-weights.pt'
    outside.write_bytes(original)
    (tmp_path / 'weights.pt').symlink_to(outside)
    with pytest.raises(ValueError, match='unsafe'):
        review_bundle(tmp_path, manifest)


def test_installer_registers_packages_and_evidence(tmp_path):
    from scripts.install_ohif_research import install
    app = tmp_path / 'platform/app'
    (app / 'public/config').mkdir(parents=True)
    (app / 'package.json').write_text('{"version":"3.11.0"}')
    (app / 'pluginConfig.json').write_text('{"extensions":[],"modes":[]}')
    install(tmp_path, {'1.2.3': {'review': 'pending'}})
    assert (tmp_path / 'extensions/tmrds-research/src/index.js').exists()
    assert json.loads((app / 'pluginConfig.json').read_text())['modes'][0]['packageName'] == '@tmrds/mode-research'
    assert '1.2.3' in (app / 'public/config/tmrds.js').read_text()
    with pytest.raises(FileExistsError):
        install(tmp_path)
