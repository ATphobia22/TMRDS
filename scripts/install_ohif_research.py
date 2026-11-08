"""Install the research packages into an existing OHIF 3.12.3 source checkout."""
import argparse
import json
from pathlib import Path
import shutil


def install(checkout: Path, evidence=None):
    repo = Path(__file__).resolve().parents[1]
    app = checkout / 'platform/app'
    package = json.loads((app / 'package.json').read_text())
    if package['version'] != '3.12.3':
        raise ValueError('research mode currently targets OHIF 3.12.3; review other versions first')
    targets = [(repo / 'extensions/ohif-tmrds-research', checkout / 'extensions/tmrds-research'),
               (repo / 'modes/ohif-tmrds-research', checkout / 'modes/tmrds-research')]
    for _, target in targets:
        if target.exists():
            raise FileExistsError(target)
    config_path = app / 'pluginConfig.json'
    config = json.loads(config_path.read_text())
    for kind, name in [('extensions', '@tmrds/extension-research'), ('modes', '@tmrds/mode-research')]:
        if not any(entry['packageName'] == name for entry in config[kind]):
            config[kind].append({'packageName': name})
    for source, target in targets:
        shutil.copytree(source, target)
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    runtime = {
        'routerBasename': '/', 'showStudyList': True,
        'extensions': [], 'modes': [], 'tmrdsEvidence': evidence or {},
        'dataSources': [{'namespace': '@ohif/extension-default.dataSourcesModule.dicomweb',
            'sourceName': 'tmrds-local', 'configuration': {
                'friendlyName': 'TMRDS local synthetic research', 'name': 'tmrds-local',
                'wadoUriRoot': 'http://127.0.0.1:8042/wado',
                'qidoRoot': 'http://127.0.0.1:8042/dicom-web',
                'wadoRoot': 'http://127.0.0.1:8042/dicom-web',
                'qidoSupportsIncludeField': True, 'imageRendering': 'wadors',
                'thumbnailRendering': 'wadors', 'supportsFuzzyMatching': False,
                'supportsWildcard': False}}],
        'defaultDataSourceName': 'tmrds-local',
    }
    (app / 'public/config/tmrds.js').write_text('window.config = ' + json.dumps(runtime) + ';\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text()) if args.evidence else {}
    install(args.checkout, evidence)
