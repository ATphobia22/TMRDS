"""Check emitted OHIF assets include the research mode and provenance panel."""
import argparse
from pathlib import Path


def verify(directory):
    if not (directory / 'index.html').is_file():
        raise ValueError('OHIF index was not built')
    contents = '\n'.join(p.read_text(errors='replace') for p in directory.rglob('*.js'))
    for marker in ('tmrds-research', 'TMRDS research review', 'not evidenced'):
        if marker not in contents:
            raise ValueError('OHIF research component missing from output: ' + marker)
    print('OHIF research mode and panel compiled; browser rendering requires a separate check')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
