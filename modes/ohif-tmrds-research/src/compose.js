export const id = '@tmrds/mode-research';
export const panel = '@tmrds/extension-research.panelModule.provenance';
export function withResearchPanel(base) {
  const extensions = { ...base.extensions, '@tmrds/extension-research': '0.1.0' };
  return { ...base, id, routeName: 'tmrds-research', displayName: 'TMRDS research review', extensions,
    routes: base.routes.map(route => ({ ...route, path: 'tmrds-research',
      layoutTemplate: (...args) => {
        const layout = route.layoutTemplate(...args);
        return { ...layout, props: { ...layout.props,
          rightPanels: [panel, ...(layout.props.rightPanels || [])], rightPanelClosed: false } };
      },
    })),
  };
}
