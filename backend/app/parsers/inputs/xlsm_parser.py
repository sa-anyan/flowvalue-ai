"""FlowValue deterministic, layout-tolerant stream/equipment extractor.

Usage: python flowvalue_smart_meb_parser.py INPUT.xlsm [--output-dir DIR]
       python flowvalue_smart_meb_parser.py INPUT.xls  [--output-dir DIR]

.xlsm/.xlsx: openpyxl read-only. Legacy .xls: xlrd (pip install xlrd).
No AI. No inferred equipment tags. Ambiguity is reported, never silently resolved.
"""
from __future__ import annotations
import argparse, csv, json, re
from collections import defaultdict
from pathlib import Path

TAG = re.compile(r'(?<![A-Za-z0-9])([A-Z]{1,4})\s*[-–]\s*(\d{2,5})(?!\d)', re.I)
STREAM_LABEL = re.compile(r'\bstream\s*(?:number|no\.?|id|#)?\s*[:#-]?\s*(\d{1,5})\b', re.I)
STREAM_HEADER = re.compile(r'\bstream\s*(?:number|no\.?|id|#)\b', re.I)
DESCRIPTION_HEADER = re.compile(r'\b(?:stream\s*)?(?:description|name)\b', re.I)
TYPES = [
    (r'\b(?:storage\s+tank|tank\s+storage)\b', 'Storage tank'),
    (r'\bbuffer\s+tank\b', 'Buffer tank'),
    (r'\b(?:pH\s+adjustment\s+unit|neutralis(?:ation|ation)\s+unit)\b', 'pH adjustment unit'),
    (r'\bbioreactor\b', 'Bioreactor'),
    (r'\b(?:biomass\s+)?settler\b', 'Settler'),
    (r'\bheat\s+exchanger\b', 'Heat exchanger'),
    (r'\b(?:centrifugal\s+)?pump\b', 'Pump'),
    (r'\bcompressor\b', 'Compressor'),
    (r'\breactor\b', 'Reactor'),
    (r'\bdistillation\s+column\b', 'Distillation column'),
    (r'\b(?:vessel|drum)\b', 'Vessel'),
]

def matrix_sheets(path):
    if path.suffix.lower() == '.xls':
        try:
            import xlrd
        except ImportError as exc:
            raise SystemExit('Legacy .xls requires: pip install xlrd') from exc
        wb = xlrd.open_workbook(str(path), on_demand=True)
        for sh in wb.sheets():
            yield sh.name, [[sh.cell_value(r,c) for c in range(sh.ncols)] for r in range(sh.nrows)]
    elif path.suffix.lower() in ('.xlsm','.xlsx'):
        from openpyxl import load_workbook
        wb = load_workbook(str(path), read_only=True, data_only=True, keep_links=False)
        try:
            for sh in wb.worksheets:
                yield sh.title, [list(row) for row in sh.iter_rows(values_only=True)]
        finally:
            wb.close()
    else:
        raise ValueError('Supported file formats: .xls, .xlsx and .xlsm')

def normalized(cell):
    return cell.strip() if isinstance(cell, str) else ''

def stream_id(v):
    if isinstance(v, bool): return None
    if isinstance(v, (int,float)) and 0 < v < 100000 and float(v).is_integer(): return str(int(v))
    if isinstance(v, str):
        if re.fullmatch(r'\d{1,5}',v.strip()): return str(int(v.strip()))
        m = STREAM_LABEL.search(v)
        if m: return str(int(m.group(1)))
    return None

def tags(text):
    return sorted(set(f'{m.group(1).upper()}-{m.group(2)}' for m in TAG.finditer(text)))

def parse_sheet(sheet, matrix):
    found=[]; issues=[]
    def add(sid,desc,r,c,method):
        if not sid or not desc: return
        if not (any(x.isalpha() for x in desc)): return
        found.append(dict(sheet=sheet,stream_id=sid,description=desc,source_cell=f'R{r+1}C{c+1}',method=method,equipment_tags=tags(desc)))

    for r,row in enumerate(matrix):
        for c,value in enumerate(row):
            t=normalized(value)
            if not t: continue
            # Detect a horizontally laid out matrix: 'Stream Number' followed by IDs,
            # with its description in the next row at the same columns.
            if STREAM_HEADER.search(t) and not STREAM_LABEL.search(t):
                if r+1<len(matrix):
                    candidates=[]
                    for cc,v in enumerate(row):
                        sid=stream_id(v)
                        if sid and cc != c and cc < len(matrix[r+1]):
                            desc=normalized(matrix[r+1][cc]);
                            if desc: candidates.append((sid,desc,cc))
                    if candidates:
                        for sid,desc,cc in candidates: add(sid,desc,r+1,cc,'horizontal-table')
                # Vertical matrix: stream number in one column, description alongside.
                for rr in range(r+1,min(len(matrix),r+10000)):
                    current=matrix[rr]
                    if c>=len(current):break
                    sid=stream_id(current[c])
                    if not sid:
                        if rr>r+1: break
                        continue
                    nearby=[(normalized(current[cc]),cc) for cc in range(max(0,c-2),min(len(current),c+4)) if cc!=c]
                    descriptions=[(d,cc) for d,cc in nearby if len(d)>8 and any(ch.isalpha() for ch in d) and not STREAM_HEADER.search(d)]
                    if len(descriptions)==1: add(sid,descriptions[0][0],rr,descriptions[0][1],'vertical-table')
                    elif len(descriptions)>1: issues.append(dict(sheet=sheet,cell=f'R{rr+1}C{c+1}',issue=f'Ambiguous adjacent description for stream {sid}'))
            # Inline descriptive label e.g. 'Stream 47: Feed from tank T-001'.
            m=STREAM_LABEL.search(t)
            if m and len(t)>len(m.group())+5:
                remainder=t[m.end():].strip(' :-—')
                add(str(int(m.group(1))),remainder,r,c,'inline-label')
    # Same stream ID can appear in several blocks; retain contradictory descriptions as issue.
    byid=defaultdict(list)
    for f in found: byid[f['stream_id']].append(f)
    canonical=[]
    for sid,items in byid.items():
        unique={x['description'].casefold().strip() for x in items}
        if len(unique)>1:
            issues.append(dict(sheet=sheet,cell=', '.join(x['source_cell'] for x in items),issue=f'Conflicting descriptions for stream {sid}'))
        # Distinct descriptions retained; identical entries deduplicated.
        seen=set()
        for x in items:
            k=(x['source_cell'], x['description'].casefold().strip())
            if k not in seen: canonical.append(x);seen.add(k)
    return canonical, issues

def classify(descriptions, tag=None):
    """Classify wording immediately before the specified equipment tag."""
    if not tag:
        return "Unclassified: review required", "equipment tag required"
    observations = set()
    for description in descriptions:
        for hit in TAG.finditer(description):
            if f"{hit.group(1).upper()}-{hit.group(2)}" != tag.upper():
                continue
            before = description[:hit.start()]
            candidates = []
            for expression, equipment in TYPES:
                for match in re.finditer(expression + r"\s*\Z", before, re.I):
                    candidates.append((match.end() - match.start(), equipment))
            if candidates:
                candidates.sort(reverse=True)
                observations.add(candidates[0][1])
    if len(observations) == 1:
        return observations.pop(), "tag-adjacent description rule"
    if len(observations) > 1:
        return "Review required: conflicting types", "conflicting tag-adjacent descriptions"
    return "Unclassified: review required", "no type immediately preceding tag"

def run(path, outdir):
    streams=[];issues=[]
    for name,matrix in matrix_sheets(path):
        s,i=parse_sheet(name,matrix);streams.extend(s);issues.extend(i)
    equipment=defaultdict(lambda:{'descriptions':[],'streams':set(),'sheets':set()})
    for s in streams:
        for tag in s['equipment_tags']:
            e=equipment[tag];e['descriptions'].append(s['description']);e['streams'].add(s['stream_id']);e['sheets'].add(s['sheet'])
    register=[]
    for tag,e in sorted(equipment.items()):
        kind,basis=classify(e['descriptions'], tag)
        register.append(dict(tag=tag,type=kind,stream_ids=', '.join(sorted(e['streams'],key=lambda a:int(a))),sheets=', '.join(sorted(e['sheets'])),classification_basis=basis))
    outdir.mkdir(parents=True,exist_ok=True)
    def output(name,rows,cols):
        with (outdir/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader()
            for row in rows:
                row=row.copy()
                if isinstance(row.get('equipment_tags'),list):row['equipment_tags']=', '.join(row['equipment_tags'])
                w.writerow(row)
    output('flowvalue_streams.csv',streams,['sheet','stream_id','description','source_cell','method','equipment_tags'])
    output('flowvalue_equipment.csv',register,['tag','type','stream_ids','sheets','classification_basis'])
    output('flowvalue_review.csv',issues,['sheet','cell','issue'])
    summary=dict(source=str(path),streams=len(streams),unique_equipment=len(register),issues=len(issues),warning='Identifies tagged equipment from descriptions only; does not infer untagged items or size equipment.')
    (outdir/'flowvalue_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('workbook',type=Path);ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args()
    print(json.dumps(run(args.workbook,args.output_dir or args.workbook.parent),indent=2))
