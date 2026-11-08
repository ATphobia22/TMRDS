import React, { useEffect, useState } from 'react';
import { researchRecords } from './records.js';
const id = '@tmrds/extension-research';

export function ResearchPanel({ servicesManager, evidence = {} }) {
  const service = servicesManager.services.displaySetService;
  const [sets, setSets] = useState(() => [...service.getActiveDisplaySets()]);
  useEffect(() => {
    const update = () => setSets([...service.getActiveDisplaySets()]);
    const subscriptions = ['DISPLAY_SETS_ADDED', 'DISPLAY_SETS_CHANGED', 'DISPLAY_SET_SERIES_METADATA_INVALIDATED']
      .filter(event => service.EVENTS[event])
      .map(event => service.subscribe(service.EVENTS[event], update));
    update();
    return () => subscriptions.forEach(sub => sub.unsubscribe());
  }, [service]);
  const records = researchRecords(sets, evidence);
  return React.createElement('section', { 'aria-label': 'TMRDS research provenance', style: { padding: 12, color: 'white', overflowWrap: 'anywhere' } },
    React.createElement('h2', null, 'TMRDS research review'),
    React.createElement('p', null, 'Research only. Checksums identify bytes; they do not establish authenticity or clinical approval.'),
    !records.length && React.createElement('p', null, 'No source instances loaded.'),
    ...records.map((record, index) => React.createElement('article', { key: `${record.instance}-${index}` },
      ...Object.entries(record).map(([key, value]) => React.createElement('p', { key }, `${key}: ${value || 'not evidenced'}`)))));
}

export default {
  id,
  getPanelModule: ({ servicesManager, configuration = {} }) => [{
    name: 'provenance', iconName: 'list-bullets', iconLabel: 'Research', label: 'TMRDS provenance',
    component: () => React.createElement(ResearchPanel, { servicesManager, evidence: configuration.evidence || globalThis.window?.config?.tmrdsEvidence || {} }),
  }],
};
