import { loadBundle, hrefOf, titleOf } from './lokf';
import { loadGraphData } from './graph-data';
import { temporalConfig } from '../temporal.config.mjs';
import { buildTemporalEvidence } from './temporal.mjs';

let evidencePromise: Promise<any> | undefined;

/** Shared by the optional route and any navigation that offers it. */
export function loadTemporalEvidence(): Promise<any> {
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
