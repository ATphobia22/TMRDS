from pathlib import Path
import yaml


def test_archive_stays_internal_and_only_proxy_publishes_loopback():
    config = yaml.safe_load(Path('deploy/imaging/compose.yml').read_text())
    archive, proxy = config['services']['imaging'], config['services']['proxy']
    assert 'ports' not in archive
    assert archive['networks'] == ['imaging']
    assert config['networks']['imaging']['internal'] is True
    assert proxy['ports'] == ['127.0.0.1:8042:8080']
    assert set(proxy['networks']) == {'imaging', 'frontend'}
    assert '@sha256:' in proxy['image'] and '@sha256:' in archive['image']
    assert 'proxy_pass http://imaging:8042;' in Path('deploy/imaging/nginx.conf').read_text()
