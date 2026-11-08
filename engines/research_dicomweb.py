"""Read-only optional dicomweb-client behind the bounded imaging transport."""
from engines.imaging_transport import ImagingSession


class ResearchDICOMweb:
    def __init__(self, base_url: str, *, local_sandbox=False, auth=None):
        from dicomweb_client.api import DICOMwebClient
        self.session = ImagingSession(base_url, local_sandbox=local_sandbox)
        self.session.auth = auth
        self._client = DICOMwebClient(base_url, session=self.session, timeout=10)
        self._client.set_http_retry_params(retry=False)

    def studies(self, *, study_uid=None, limit=25):
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        filters = {}
        if study_uid is not None:
            self._uid(study_uid)
            filters["StudyInstanceUID"] = study_uid
        result = self._client.search_for_studies(limit=limit, search_filters=filters)
        if not isinstance(result, list) or len(result) > limit:
            raise ValueError("upstream exceeded record budget")
        return result

    @staticmethod
    def _uid(value):
        import re
        if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", value):
            raise ValueError("invalid DICOM UID")

    def metadata(self, study_uid, series_uid, instance_uid):
        for uid in (study_uid, series_uid, instance_uid):
            self._uid(uid)
        return self._client.retrieve_instance_metadata(study_uid, series_uid, instance_uid)

    def close(self):
        self.session.close()
