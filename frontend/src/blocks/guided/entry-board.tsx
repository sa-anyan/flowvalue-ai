'use client';
import { useEffect, useMemo, useState } from 'react';
import { MAX_WORKBOOK_BYTES } from '@/lib/upload-limits';
import { equipmentCards, list, obj, strings, text, type EquipmentCardModel, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import { EquipmentInspector } from './equipment-inspector';
import { OriginChip, Panel, RunBar, type StageProps } from './flow';
import { matchChip, pending, QuickMatchPanel, useQuickMatches } from './quick-match';
import { AutopilotCard } from './autopilot';
import { RevenueSetup } from './revenue-setup';

const WORKBOOK = /\.(xlsx|xls|xlsm)$/i;

/**
 * Entry = a calm, empty board. Dropping the M&E balance extracts equipment,
 * which pops in as cards on the right. "Run equipment" prices them with Python
 * and swipes to the Equipment page.
 */
export function EntryBoard(props: StageProps) {
  const { hook, equipment } = props;
  const state = hook.state;
  const [file, setFile] = useState<File | null>(null),
    [description, setDescription] = useState(''),
    [revenue, setRevenue] = useState(''),
    [years, setYears] = useState(20),
    [construction, setConstruction] = useState(2),
    [useAI, setUseAI] = useState(false),
    [dragging, setDragging] = useState(false),
    [selected, setSelected] = useState<{ card: EquipmentCardModel; mode: 'inspect' | 'manual' | 'research' } | null>(null),
    [confirm, setConfirm] = useState(false),
    [versions, setVersions] = useState<Row[]>([]),
    [briefOpen, setBriefOpen] = useState(false),
    [previous, setPrevious] = useState<{ id: string; name: string } | null>(null);
  useEffect(() => setUseAI(hook.aiEnabled), [hook.aiEnabled]);
  useEffect(() => {
    void api<Row[]>('versions')
      .then((v) => setVersions(Array.isArray(v) ? v : []))
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!state) return;
    setDescription(text(state.process_description ?? state.description));
    setRevenue(text(state.revenue_description));
    const schedule = obj(state.analysis_schedule);
    if (schedule.analysis_years) setYears(Number(schedule.analysis_years));
    if (schedule.construction_years !== undefined) setConstruction(Number(schedule.construction_years));
  }, [state?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const cards = useMemo(() => equipmentCards(state, equipment.value, hook.catalogue), [state, equipment.value, hook.catalogue]);
  const extracting = Boolean(state?.running) && !cards.length;
  const approved = state?.engineering_data_approved === true;
  const running = Boolean(state?.running) || hook.busy;

  function choose(next: File | undefined | null) {
    if (!next) return;
    if (!WORKBOOK.test(next.name)) return hook.setError('Choose an Excel workbook (.xlsx, .xls or .xlsm).');
    if (next.size > MAX_WORKBOOK_BYTES) return hook.setError('Choose a workbook up to 20 MiB.');
    hook.setError('');
    if (state && hook.id) {
      // A new workbook is a new study: leave the open one (it stays saved) and
      // start from a blank board, so its equipment and brief never carry over.
      if (state.running) return hook.setError('Wait for the current calculation to finish, then choose the new workbook.');
      setPrevious({ id: hook.id, name: text(state.filename) || 'previous study' });
      setSelected(null);
      setConfirm(false);
      setDescription('');
      setRevenue('');
      setYears(20);
      setConstruction(2);
      setBriefOpen(true);
      hook.clear();
    }
    setFile(next);
  }
  async function extract() {
    let key = hook.id;
    if (file) {
      const form = new FormData();
      form.set('file', file);
      form.set('description', description);
      form.set('revenue_description', revenue);
      form.set('use_ai', String(useAI));
      form.set('analysis_years', String(years));
      form.set('construction_years', String(construction));
      key = (await api<Row>('assessments', { method: 'POST', body: form })).id as string;
      hook.select(key);
      setFile(null);
      setPrevious(null);
    }
    if (!key) throw new Error('Choose a workbook first.');
    await api(
      `assessments/${key}/engineering/run`,
      post({ use_ai: useAI, process_description: description, revenue_description: revenue, prepare_only: true, analysis_years: years, construction_years: construction }),
    );
  }
  const runEquipment = () => {
    if (!approved) return setConfirm(true);
    void props.advance(() => equipment.save('User reviewed equipment parameters on the guided Entry board'));
  };
  // After quick match saves the choices: price straight away. No draft save here,
  // so an older unsaved board copy can never overwrite the confirmed models.
  const priceNow = () => {
    if (!approved) return setConfirm(true);
    void props.advance();
  };
  // Quick match: deterministic, no AI. Pops up once per assessment when items need a model.
  const quick = useQuickMatches(hook.id, state?.revision, cards.length > 0 && !state?.running);
  const matches = quick.result;
  const matchByKey = useMemo(() => new Map((matches?.matches || []).map((m) => [m.equipment_key, m])), [matches]);
  const awaiting = (matches?.matches || []).filter(pending).length;
  const [quickOpen, setQuickOpen] = useState(false),
    [quickSeen, setQuickSeen] = useState<string | null>(null);
  useEffect(() => {
    if (!matches || !hook.id || quickSeen === hook.id) return;
    if (matches.matches.some((m) => pending(m) && m.options.length)) setQuickOpen(true);
    setQuickSeen(hook.id);
  }, [matches, hook.id, quickSeen]);
  const counts = {
    total: cards.length,
    matched: cards.filter((c) => c.status !== 'unmatched').length,
    inputs: cards.filter((c) => c.status === 'needs_inputs' || c.status === 'unmatched').length,
  };
  const empty = !state;

  return (
    <div className={`gf-board ${empty ? 'gf-board-empty' : ''}`}>
      <div className="gf-lane gf-lane-source">
        <span className="gf-kicker">01 · YOUR PROCESS</span>
        <label
          className={`gf-drop ${dragging ? 'gf-drop-active' : ''} ${file ? 'gf-drop-ready' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            choose(e.dataTransfer.files[0]);
          }}
        >
          <span className="gf-drop-icon" aria-hidden="true">
            ⇪
          </span>
          <strong>{file ? file.name : state ? state.filename : 'Drop your mass & energy balance'}</strong>
          <small>{file ? 'Ready to extract' : state ? 'Drop another workbook to start a new assessment' : 'or click to choose · .xlsx · .xls · .xlsm · up to 20 MiB'}</small>
          <input type="file" accept=".xlsx,.xls,.xlsm" className="gf-sr-only" onChange={(e) => choose(e.target.files?.[0])} />
        </label>

        <details className="gf-brief" open={briefOpen || empty} onToggle={(e) => setBriefOpen((e.target as HTMLDetailsElement).open)}>
          <summary>Project brief</summary>
          <label className="gf-field">
            <span>Describe your process</span>
            <textarea value={description} maxLength={12000} onChange={(e) => setDescription(e.target.value)} placeholder="Inputs, outputs, location and design requirements." />
          </label>
          <div className="gf-grid-2">
            <label className="gf-field">
              <span>Analysis years</span>
              <input type="number" min="1" max="60" value={years} onChange={(e) => setYears(Number(e.target.value))} />
            </label>
            <label className="gf-field">
              <span>Construction years</span>
              <input type="number" min="0" max="10" value={construction} onChange={(e) => setConstruction(Number(e.target.value))} />
            </label>
          </div>
          <label className="gf-check">
            <input type="checkbox" checked={useAI} disabled={!hook.aiEnabled} onChange={(e) => setUseAI(e.target.checked)} />
            <span>
              AI analyst interprets the workbook and proposes models (provisional; usage charges apply).
              {!hook.aiEnabled && ' AI is switched off on this server.'}
            </span>
          </label>
        </details>
        <button type="button" className="gf-primary gf-extract" disabled={running || (!file && !hook.id)} onClick={() => void hook.action(extract)}>
          {file ? `Extract equipment from ${file.name}` : !state ? 'Extract equipment' : 'Re-extract with this brief'}
        </button>
        {state && !previous && <RevenueSetup props={props} />}
        {previous && (
          <p className="gf-note">
            New study: {previous.name} is saved and unchanged.{' '}
            <button
              type="button"
              className="gf-link"
              onClick={() => {
                setFile(null);
                hook.select(previous.id);
                setPrevious(null);
              }}
            >
              Back to {previous.name}
            </button>
          </p>
        )}

        {empty && versions.length > 0 && (
          <div className="gf-saved">
            <span className="gf-kicker">OR CONTINUE</span>
            {versions.slice(-6).reverse().map((v) => (
              <button
                key={text(v.id)}
                type="button"
                className="gf-saved-item"
                disabled={hook.busy}
                onClick={() => void hook.action(async () => hook.select(text((await api<Row>(`versions/${text(v.id)}/open`, post({}))).id)))}
              >
                {text(v.name)}
                <small>Opens a copy of this saved version</small>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="gf-lane gf-lane-cards" aria-live="polite">
        {cards.length > 0 && <AutopilotCard props={props} />}
        <div className="gf-lane-head">
          <span className="gf-kicker">02 · EQUIPMENT FROM YOUR WORKBOOK</span>
          {cards.length > 0 && (
            <span className="gf-muted">
              {counts.total} items · {counts.matched} with a cost model · {counts.inputs} need inputs
            </span>
          )}
          {matches && (
            <button type="button" className="gf-secondary gf-qm-open" onClick={() => setQuickOpen(true)}>
              Quick match{awaiting ? ` · ${awaiting} to confirm` : ' · all confirmed'}
            </button>
          )}
          {quick.error && (
            <span className="gf-warn gf-qm-error" role="alert">
              Quick match unavailable: {quick.error}{' '}
              <button type="button" className="gf-link" onClick={quick.retry}>
                Retry
              </button>
            </span>
          )}
        </div>
        {empty && (
          <div className="gf-placeholder">
            <p>Equipment will appear here as it is read from your workbook.</p>
          </div>
        )}
        {extracting && (
          <div className="gf-skeletons" role="status">
            <span className="gf-sr-only">Reading workbook…</span>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="gf-skeleton" style={{ ['--i' as string]: i }} />
            ))}
          </div>
        )}
        {state && !extracting && !cards.length && (
          <div className="gf-placeholder">
            <p>No equipment has been extracted yet. Choose “Extract equipment”.</p>
          </div>
        )}
        <ul className="gf-cards">
          {cards.map((c, i) => (
            <li key={c.key} className="gf-card-pop" style={{ ['--i' as string]: Math.min(i, 24) }}>
              <button type="button" className={`gf-card gf-card-${c.status}`} onClick={() => setSelected({ card: c, mode: 'inspect' })}>
                <span className="gf-card-top">
                  <strong>{c.tag}</strong>
                  <span className={`gf-pill gf-pill-${c.status}`}>{c.statusLabel}</span>
                </span>
                <span className="gf-card-name">{c.name}</span>
                <span className="gf-card-model">{c.model}</span>
                {(() => {
                  const chip = matchChip(matchByKey.get(c.key));
                  return chip && <span className={`gf-qm-tag gf-qm-${chip.tone}`}>{chip.label}</span>;
                })()}
                <span className="gf-card-foot">
                  <OriginChip origin={c.modelOrigin === 'ai' ? 'AI · provisional' : c.modelOrigin === 'user' ? 'Your input' : 'Unreviewed'} />
                  <small>
                    {c.requiredInputs.some((r) => r.required)
                      ? `${c.requiredInputs.filter((r) => r.required && r.value !== null && r.value !== undefined && r.value !== '').length}/${c.requiredInputs.filter((r) => r.required).length} required inputs`
                      : c.size}
                  </small>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {strings(state?.revenue_questions).length > 0 && (
          <div className="gf-note" role="status">
            <strong>Revenue needs your input under “How does this project earn money?”</strong>
            <ul className="gf-issue-list">
              {strings(state?.revenue_questions).map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {state && (
        <RunBar
          label="Run equipment"
          busy={hook.busy}
          disabled={!cards.length || Boolean(state.running)}
          onRun={runEquipment}
          status={
            <span className="gf-run-status">
              <strong>{equipment.dirty ? 'Unsaved board edits will be saved first' : approved ? 'Engineering data approved' : 'Review the cards, then run equipment'}</strong>
              {hook.aiEnabled && (
                <label className="gf-check gf-run-ai">
                  <input type="checkbox" checked={props.aiSizing} onChange={(e) => props.setAiSizing(e.target.checked)} />
                  <span>AI proposes missing sizing inputs (provisional, shown for review)</span>
                </label>
              )}
            </span>
          }
          note={
            props.aiSizing && hook.aiEnabled
              ? 'Python prices every card with its confirmed model. The AI only fills sizing inputs your data lacks, each labelled as an assumption; usage charges apply.'
              : 'Python prices every card with its saved model. No AI is used: items without sizing inputs stay unpriced until you enter them.'
          }
        />
      )}

      {quickOpen && matches && (
        <QuickMatchPanel
          key={`${hook.id}-${matches.revision}`}
          result={matches}
          props={props}
          onClose={() => setQuickOpen(false)}
          onPrice={priceNow}
          onInspect={(key) => {
            const card = cards.find((c) => c.key === key);
            setQuickOpen(false);
            if (card) setSelected({ card, mode: 'inspect' });
          }}
        />
      )}
      {selected && (
        <EquipmentInspector
          key={selected.card.key}
          card={cards.find((c) => c.key === selected.card.key) || selected.card}
          props={props}
          initialMode={selected.mode}
          onClose={() => setSelected(null)}
          onRun={() => {
            setSelected(null);
            runEquipment();
          }}
        />
      )}
      {confirm && state && (
        <Panel
          title="Approve engineering data and run equipment?"
          kicker="CONFIRM"
          onClose={() => setConfirm(false)}
          footer={
            <>
              <button type="button" className="gf-secondary" onClick={() => setConfirm(false)}>
                Keep reviewing
              </button>
              <button
                type="button"
                className="gf-primary"
                onClick={() => {
                  setConfirm(false);
                  void props.advance(async () => {
                    await equipment.save('User reviewed equipment parameters on the guided Entry board');
                    const latest = await api<Row>('assessments/' + hook.id);
                    await api(`assessments/${hook.id}/engineering-approval`, post({ revision: latest.revision }));
                  });
                }}
              >
                Approve & run equipment
              </button>
            </>
          }
        >
          <p>
            Downstream stages only run from approved engineering data. Approving records that you reviewed the extracted streams and the {cards.length} equipment cards on this
            board (revision {state.revision}). You can still edit everything afterwards; changes mark results for recalculation.
          </p>
        </Panel>
      )}
    </div>
  );
}
