'use client';
import { useEffect, useState } from 'react';
import { MAX_WORKBOOK_BYTES } from '@/lib/upload-limits';
import { launchStatus, list, obj, strings, studyReport, text, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import { RunBar, type StageProps } from './flow';
import { EntryBoard } from './entry-board';
import { RevenueSetup } from './revenue-setup';
import { QuickQuestions } from './quick-questions';

const WORKBOOK = /\.(xlsx|xls|xlsm)$/i;

/**
 * Entry, Save & go: upload the M&E balance, tick AI, Save. Everything then runs
 * in the background (reading, AI review, models, equipment, CAPEX, OPEX) while
 * the page turns into "How does this project earn money?". When revenue is
 * defined the user continues to Equipment, which is usually already priced.
 * The extracted-data board stays one click away for review.
 */
export function EntryStart(props: StageProps) {
  const { hook } = props;
  const state = hook.state;
  const [review, setReview] = useState(false);
  const [fresh, setFresh] = useState(false); // the user chose to upload a new workbook
  useEffect(() => {
    setReview(false);
    setFresh(false);
  }, [state?.id]);
  if (!state || fresh) return <UploadStart props={props} onCancel={state ? () => setFresh(false) : undefined} />;
  if (review)
    return (
      <>
        <p className="gf-note">
          Reviewing the extracted data.{' '}
          <button type="button" className="gf-link" onClick={() => setReview(false)}>
            Back to revenue
          </button>
        </p>
        <EntryBoard {...props} />
      </>
    );
  return <RevenueStep props={props} onReview={() => setReview(true)} onNew={() => setFresh(true)} />;
}

function UploadStart({ props, onCancel }: { props: StageProps; onCancel?: () => void }) {
  const { hook } = props;
  const [file, setFile] = useState<File | null>(null),
    [useAI, setUseAI] = useState(false),
    [dragging, setDragging] = useState(false);
  useEffect(() => setUseAI(hook.aiEnabled), [hook.aiEnabled]);
  function choose(next: File | undefined | null) {
    if (!next) return;
    if (!WORKBOOK.test(next.name)) return hook.setError('Choose an Excel workbook (.xlsx, .xls or .xlsm).');
    if (next.size > MAX_WORKBOOK_BYTES) return hook.setError('Choose a workbook up to 20 MiB.');
    hook.setError('');
    setFile(next);
  }
  async function save() {
    if (!file) return;
    const form = new FormData();
    form.set('file', file);
    form.set('use_ai', String(useAI));
    form.set('analysis_years', '20');
    form.set('construction_years', '2');
    const key = (await api<Row>('assessments', { method: 'POST', body: form })).id as string;
    await api(`assessments/${key}/launch`, post({ use_ai: useAI }));
    hook.select(key);
  }
  return (
    <section className="gf-start" aria-labelledby="gf-start-h">
      <span className="gf-kicker">01 · YOUR PROCESS</span>
      <h2 id="gf-start-h">Upload your mass &amp; energy balance</h2>
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
        <strong>{file ? file.name : 'Drop your mass & energy balance'}</strong>
        <small>{file ? 'Ready — press Save' : 'or click to choose · .xlsx · .xls · .xlsm · up to 20 MiB'}</small>
        <input type="file" accept=".xlsx,.xls,.xlsm" className="gf-sr-only" onChange={(e) => choose(e.target.files?.[0])} />
      </label>
      <label className="gf-check">
        <input type="checkbox" checked={useAI} disabled={!hook.aiEnabled} onChange={(e) => setUseAI(e.target.checked)} />
        <span>
          Use the AI analyst (reviews the workbook, picks and sizes equipment, explains every stage; usage charges apply).
          {!hook.aiEnabled && ' AI is switched off on this server.'}
        </span>
      </label>
      <div className="gf-inline-actions">
        {onCancel && (
          <button type="button" className="gf-link" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button type="button" className="gf-primary" disabled={!file || hook.busy} onClick={() => void hook.action(save)}>
          Save
        </button>
      </div>
    </section>
  );
}

function RevenueStep({ props, onReview, onNew }: { props: StageProps; onReview: () => void; onNew: () => void }) {
  const { hook, go } = props;
  const state = hook.state;
  const status = launchStatus(state);
  const streams = list(studyReport(state).entities).filter((e) => e.kind === 'material');
  const revenueSet = list(obj(obj(state?.plan).operating_economics).sales).length > 0 || strings(state?.inbox).includes('revenue_setup');
  return (
    <div className="gf-start">
      <p className={`gf-launch gf-launch-${status.tone}`} role="status" aria-live="polite">
        {status.tone === 'working' && <span className="gf-spinner" aria-hidden="true" />}
        <span>{status.text}</span>
        <span className="gf-launch-file">{text(state?.filename)}</span>
      </p>
      {streams.length === 0 ? (
        <section className="gf-revenue-setup" aria-busy="true">
          <span className="gf-kicker">HOW DOES THIS PROJECT EARN MONEY?</span>
          <p className="gf-muted">Reading your workbook… the streams appear here in a few seconds.</p>
          <div className="gf-analyst-skeleton" aria-hidden="true">
            <span />
            <span />
          </div>
        </section>
      ) : (
        <>
          <RevenueSetup props={props} />
          <QuickQuestions props={props} />
        </>
      )}
      <p className="gf-muted gf-start-links">
        <button type="button" className="gf-link" onClick={onReview} disabled={streams.length === 0}>
          Review extracted data
        </button>
        {' · '}
        <button type="button" className="gf-link" onClick={onNew}>
          Upload a different workbook
        </button>
      </p>
      <RunBar
        status={<strong>{revenueSet ? 'Revenue saved' : 'Define revenue, or continue and add it later'}</strong>}
        label="Continue to Equipment"
        note="FlowValue keeps working in the background; equipment is usually priced by the time you get there."
        disabled={streams.length === 0}
        onRun={() => go('equipment')}
      />
    </div>
  );
}
