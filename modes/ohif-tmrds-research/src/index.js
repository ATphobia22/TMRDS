import longitudinal from '@ohif/mode-longitudinal';
import { id, withResearchPanel } from './compose.js';
export default {
  id,
  extensionDependencies: { ...longitudinal.extensionDependencies, '@tmrds/extension-research': '0.1.0' },
  modeFactory: options => withResearchPanel(longitudinal.modeFactory(options)),
};
