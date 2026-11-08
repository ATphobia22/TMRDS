"""Explicit local research operations: bundle review and human annotation submission."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    studies = sub.add_parser('studies')
    studies.add_argument('--study-uid')
    sub.add_parser('annotation-info')
    review = sub.add_parser('review-bundle')
    review.add_argument('directory', type=Path)
    review.add_argument('manifest', type=Path)
    annotation = sub.add_parser('submit-label')
    annotation.add_argument('--image', required=True)
    annotation.add_argument('--label', type=Path, required=True)
    annotation.add_argument('--reviewer', required=True)
    for key in ('study', 'series', 'instance'):
        annotation.add_argument('--' + key, required=True)
    annotation.add_argument('--confirm-human-review', action='store_true')
    args = parser.parse_args()
    if args.action == 'studies':
        from engines.research_dicomweb import ResearchDICOMweb
        config = json.loads(Path('data/imaging-demo/orthanc.json').read_text())
        client = ResearchDICOMweb('http://127.0.0.1:8042/dicom-web', local_sandbox=True,
            auth=('research', config['RegisteredUsers']['research']))
        try:
            result = client.studies(study_uid=args.study_uid)
        finally:
            client.close()
    elif args.action == 'annotation-info':
        from engines.human_annotation import HumanAnnotationClient
        client = HumanAnnotationClient()
        try:
            result = client.info()
        finally:
            client.close()
    elif args.action == 'review-bundle':
        from engines.model_bundle_review import review_bundle
        result = review_bundle(args.directory, json.loads(args.manifest.read_text()))
    else:
        from engines.human_annotation import HumanAnnotationClient
        client = HumanAnnotationClient()
        try:
            result = client.submit(image_id=args.image, label=args.label, reviewer=args.reviewer,
                source_uids={key: getattr(args, key) for key in ('study', 'series', 'instance')},
                confirmed=args.confirm_human_review)
        finally:
            client.close()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
