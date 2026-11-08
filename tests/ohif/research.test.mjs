import test from 'node:test';
import assert from 'node:assert/strict';
import { researchRecords } from '../../extensions/ohif-tmrds-research/src/records.js';
import { withResearchPanel, panel } from '../../modes/ohif-tmrds-research/src/compose.js';

test('provenance binds every UID and never fabricates review', () => {
  const sets = [{ StudyInstanceUID: '1.2', SeriesInstanceUID: '1.3', instances: [{ SOPInstanceUID: '1.4' }] }];
  assert.equal(researchRecords(sets)[0].review, 'pending');
  const evidence = { '1.4': { study: '1.2', series: '1.3', instance: '1.4', sha256: 'a'.repeat(64), review: 'research_reviewed' } };
  assert.equal(researchRecords(sets, evidence)[0].sha256, 'a'.repeat(64));
  evidence['1.4'].study = 'another study';
  assert.equal(researchRecords(sets, evidence)[0].sha256, 'not evidenced');
});

test('mode retains base viewport/lifecycle and adds visible provenance panel', () => {
  const onModeEnter = () => {};
  const base = { onModeEnter, extensions: { cornerstone: '3' }, routes: [{
    path: 'viewer', layoutTemplate: () => ({ id: 'layout', props: { viewports: ['viewport'], rightPanels: ['measurements'] } }),
  }] };
  const mode = withResearchPanel(base);
  const layout = mode.routes[0].layoutTemplate();
  assert.equal(mode.onModeEnter, onModeEnter);
  assert.deepEqual(layout.props.viewports, ['viewport']);
  assert.deepEqual(layout.props.rightPanels, [panel, 'measurements']);
  assert.equal(mode.routeName, 'tmrds-research');
  assert.equal(base.routes[0].path, 'viewer');
});
