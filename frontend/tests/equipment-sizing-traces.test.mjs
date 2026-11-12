import assert from 'node:assert/strict';
import test from 'node:test';
import { findEquipmentSizingTrace } from '../src/lib/equipment-sizing-traces.ts';

test('equipment cards use record keys when trace order differs', () => {
  const traces = [
    {equipment_key: 'east:t104', status: 'versioned', applicability_notes: ['East warning']},
    {equipment_key: 'west:t104', status: 'versioned', applicability_notes: ['West warning']},
    {equipment_key: null, status: 'unversioned', applicability_notes: ['Legacy']},
  ];
  const cards = [
    {key: 'west:t104', tag: 'T-104'},
    {key: 'east:t104', tag: 'T-104'},
    {key: 'missing:t104', tag: 'T-104'},
    {tag: 'T-104'},
  ];
  assert.deepEqual(cards.map(card => findEquipmentSizingTrace(traces, card.key)?.applicability_notes), [
    ['West warning'], ['East warning'], undefined, undefined,
  ]);
});
