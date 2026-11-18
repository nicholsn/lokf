import { loadBundle, hrefOf, titleOf } from './lokf';
import { loadGraphData } from './graph-data';
import { temporalConfig } from '../temporal.config.mjs';
import { buildTemporalEvidence } from './temporal.mjs';

let evidencePromise: Promise<any> | undefined;

/**
 * Shared by the optional route and any navigation that offers it. Resolves to
 * undefined, so no page or link appears, unless the config enables the view.
 */
export function loadTemporalEvidence(): Promise<any> {
  if (!temporalConfig.enabled) return Promise.resolve(undefined);
  evidencePromise ||= Promise.all([loadBundle(), loadGraphData()]).then(([{ concepts }, graph]) =>
    buildTemporalEvidence(concepts.map(c => ({
      id: c.id,
      title: titleOf(c),
      type: c.data.type,
      href: hrefOf(c),
      data: c.data,
    })), graph, temporalConfig));
  return evidencePromise;
}
