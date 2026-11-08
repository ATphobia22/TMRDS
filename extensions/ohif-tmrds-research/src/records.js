// Evidence is supplied by a locally reviewed sidecar, keyed by exact source UID.
export function researchRecords(displaySets, evidence = {}) {
  return displaySets.flatMap(ds => (ds.instances || []).map(instance => {
    const study = instance.StudyInstanceUID || ds.StudyInstanceUID;
    const series = instance.SeriesInstanceUID || ds.SeriesInstanceUID;
    const sop = instance.SOPInstanceUID;
    const source = evidence[sop];
    const matched = source?.study === study && source?.series === series && source?.instance === sop;
    return { study, series, instance: sop,
      sha256: matched && /^[a-f0-9]{64}$/.test(source.sha256 || '') ? source.sha256 : 'not evidenced',
      source: matched ? source.source || 'not evidenced' : 'not evidenced',
      review: matched && ['pending', 'human_submitted', 'research_reviewed', 'rejected'].includes(source.review)
        ? source.review : 'pending',
      reviewer: matched ? source.reviewer || 'not evidenced' : 'not evidenced',
    };
  }));
}
