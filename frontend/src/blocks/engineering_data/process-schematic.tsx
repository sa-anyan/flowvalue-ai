'use client';
import {useMemo,useRef,useState} from 'react';
type Value=Record<string,unknown>;
type Entity={key:string;identifier:string;kind:string;values:Value[];stream_keys?:string[]};
type Connection={stream_key:string;equipment_key:string;role:string;basis?:string;evidence_ids?:string[];status?:string};
export function ProcessSchematic({report}:{report:{entities:Entity[];connections?:Connection[]}}){
 const [mode,setMode]=useState<'2d'|'3d'>('2d'),[selected,setSelected]=useState(''),[query,setQuery]=useState(''),[angle,setAngle]=useState(30);
 const svg=useRef<SVGSVGElement>(null);
 const model=useMemo(()=>{
  const equipment=report.entities.filter(e=>e.kind==='equipment');
  const byKey=new Map(report.entities.map(e=>[e.key,e]));
  const nodes=equipment.map((e,i)=>({...e,x:45+(i%4)*240,y:45+Math.floor(i/4)*140}));
  const positions=new Map(nodes.map(n=>[n.key,n]));
  const edges:{id:string;source:string;target:string;stream:Entity;references:string[];reviewStatus:string}[]=[];
  for(const stream of report.entities.filter(e=>e.kind!=='equipment')){
   const relations=(report.connections||[]).filter(c=>c.stream_key===stream.key);
   const sources=Array.from(new Set(relations.filter(c=>c.role==='source'&&positions.has(c.equipment_key)).map(c=>c.equipment_key)));
   const targets=Array.from(new Set(relations.filter(c=>c.role==='destination'&&positions.has(c.equipment_key)).map(c=>c.equipment_key)));
   // Multiple source/target candidates remain unresolved; no cartesian invented pipes.
   if(sources.length===1&&targets.length===1&&sources[0]!==targets[0])edges.push({id:stream.key,source:sources[0],target:targets[0],stream,references:Array.from(new Set(relations.flatMap(c=>c.evidence_ids||[]))),reviewStatus:'Recorded association — not physically verified'});
  }
  return {nodes,positions,edges,byKey,height:Math.max(220,Math.ceil(nodes.length/4)*140+40)};
 },[report]);
 const visible=model.nodes.filter(n=>!query||[n.identifier,...n.values.filter(v=>['name','type','description'].includes(String(v.property))).map(v=>v.normalized_value??v.original_value)].join(' ').toLowerCase().includes(query.toLowerCase()));
 const related=model.edges.filter(e=>!selected||e.source===selected||e.target===selected);
 const associations=selected?(report.connections||[]).filter(c=>c.equipment_key===selected):[];
 function download(name:string,content:string,type:string){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 function exportObj(){const vertices=model.nodes.flatMap(n=>[[n.x,n.y,0],[n.x+165,n.y,0],[n.x+165,n.y+65,0],[n.x,n.y+65,0],[n.x,n.y,25],[n.x+165,n.y,25],[n.x+165,n.y+65,25],[n.x,n.y+65,25]]);let out='# FlowValue schematic ONLY; arbitrary coordinates, not plant geometry or pipe routing\n'+vertices.map(v=>'v '+v.join(' ')).join('\n')+'\n';model.nodes.forEach((n,i)=>{const b=i*8;out+='# '+n.identifier+'\n';for(const face of [[1,2,3,4],[5,6,7,8],[1,2,6,5],[2,3,7,6],[3,4,8,7],[4,1,5,8]])out+='f '+face.map(k=>k+b).join(' ')+'\n';});download('FlowValue-schematic-equipment.obj',out,'text/plain');}
 return <section className="process-schematic" aria-label="Interactive process schematic"><div className="sizing-editor-title"><div><h2>Process map</h2><small>Source-linked schematic · {model.nodes.length} equipment · {model.edges.length} proposed directed associations</small></div><div className="segmented"><button aria-pressed={mode==='2d'} onClick={()=>setMode('2d')}>2D</button><button aria-pressed={mode==='3d'} onClick={()=>setMode('3d')}>3D schematic</button></div></div>
 <div className="toolbar"><input type="search" aria-label="Find equipment in process map" placeholder="Find equipment…" value={query} onChange={e=>setQuery(e.target.value)}/><button className="secondary" onClick={()=>setSelected('')}>Show all links</button><button className="secondary" onClick={()=>{if(svg.current)download('FlowValue-process-map.svg',new XMLSerializer().serializeToString(svg.current),'image/svg+xml');}}>Export 2D SVG</button><button className="secondary" onClick={exportObj}>Export schematic OBJ</button>{mode==='3d'&&<label>Tilt<input type="range" min="0" max="55" value={angle} onChange={e=>setAngle(Number(e.target.value))}/></label>}</div>
 <div className="process-map-viewport"><svg ref={svg} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 1000 ${model.height}`} role="img" aria-label="Workbook equipment and directed stream relationships" style={mode==='3d'?{transform:`perspective(1400px) rotateX(${angle}deg) rotateZ(-3deg)`,transformOrigin:'50% 20%'}:undefined}>
 <title>FlowValue source-linked process schematic; layout is not physical geometry</title><defs><marker id="process-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#437d9c"/></marker></defs><rect width="1000" height={model.height} fill="#f6f8f5"/>
 {related.map(edge=>{const a=model.positions.get(edge.source)!,b=model.positions.get(edge.target)!;const x1=a.x+82,y1=a.y+65,x2=b.x+82,y2=b.y;return <g key={edge.id}><path d={`M${x1} ${y1} C${x1} ${y1+45},${x2} ${y2-45},${x2} ${y2}`} fill="none" stroke="#437d9c" strokeWidth={selected?2.5:1.3} strokeDasharray="6 5" opacity={selected?1:.65} markerEnd="url(#process-arrow)"/><title>Stream {edge.stream.identifier}; {edge.reviewStatus}; evidence {edge.references.join(', ')}</title></g>;})}
 {visible.map(n=><g key={n.key} role="button" tabIndex={0} aria-label={`Inspect ${n.identifier}`} aria-pressed={selected===n.key} onClick={()=>setSelected(n.key)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(n.key);}}} style={{cursor:'pointer'}}><rect x={n.x} y={n.y} width="165" height="65" rx="9" fill={selected===n.key?'#d8e7bd':'#fff'} stroke={selected===n.key?'#366b57':'#bbc9c0'} strokeWidth="1.5"/><text x={n.x+12} y={n.y+26} fontSize="15" fontFamily="sans-serif" fill="#20392c">{n.identifier}</text><text x={n.x+12} y={n.y+47} fontSize="10" fontFamily="sans-serif" fill="#567164">{String([...n.values].reverse().find(v=>v.property==='type')?.normalized_value||'Inspect stream evidence').slice(0,25)}</text></g>)}
 </svg></div>
 {selected&&<details open><summary>{model.positions.get(selected)?.identifier} · recorded stream relationships</summary><div className="schematic-links">{associations.map((c,i)=><div key={i}><strong>Stream {model.byKey.get(c.stream_key)?.identifier||'Unresolved'}</strong><span>{c.role==='mention'?'Association only; direction not established':c.role==='source'?'Leaving equipment':'Entering equipment'}</span><small>{c.evidence_ids?.join(', ')} · {c.status||'Review required'}</small></div>)}</div></details>}
 <small>Equipment layout and 3D boxes are schematic, not design geometry. Dashed arrows show unique recorded source/destination proposals, not verified physical pipework. Other streams remain in the register; no physical connection, oxygen-production claim or balance validation is invented.</small></section>;
}
