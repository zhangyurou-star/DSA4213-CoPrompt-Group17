// Offline logic checks with a minimal DOM stub. This is not browser rendering QA.
const fs=require('fs'), path=require('path'), vm=require('vm'), assert=require('assert/strict');
const root=path.resolve(__dirname,'../../experiments/120_fresh_v0.6/outputs/fresh120_analysis');
let checks=0;
function ok(value,message){assert.ok(value,message);checks++;}
function harness(slot, options={}){
 const html=fs.readFileSync(path.join(root,'review_forms',`reviewer_${slot}.html`),'utf8');
 const data=JSON.parse(html.match(/<script id="packet" type="application\/json">([\s\S]*?)<\/script>/)[1]);
 const code=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
 const map=new Map(), storage=options.storage||new Map(), downloads=[], urls=new Map();
 class Element{
  constructor(tag='div'){this.tagName=tag;this.value='';this.checked=false;this.disabled=false;this.readOnly=false;this.children=[];this.style={};this.dataset={};this.files=[];this._text='';this.classList={toggle(){}};}
  set innerHTML(v){this._html=v;for(const m of v.matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"[^>]*>/g)){const e=new Element(m[1]);e.id=m[2];map.set(e.id,e);}}
  get innerHTML(){return this._html||'';}set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text;}
  append(e){this.children.push(e);}setAttribute(k,v){this[k]=v;}addEventListener(k,fn){this['on'+k]=fn;}scrollIntoView(){}remove(){}
  click(){if(this.tagName==='a')downloads.push({name:this.download,blob:urls.get(this.href)});else this.onclick?.();}
 }
 const doc={body:new Element('body'),title:'',getElementById:id=>{if(!map.has(id))throw Error('Missing DOM id: '+id);return map.get(id);},createElement:tag=>new Element(tag)};
 const mount=new Element();mount.innerHTML=html.split('<script id="packet"')[0];
 map.set('packet',new Element('script'));map.get('packet').textContent=JSON.stringify(data);
 map.get('filter').value='all';
 const localStorage={getItem:k=>{if(options.storageFails)throw Error('blocked');return storage.get(k)||null;},setItem:(k,v)=>{if(options.storageFails)throw Error('blocked');storage.set(k,v);}};
 const window={confirm:()=>true,print(){},alert(){}};
 const context={document:doc,window,location:{pathname:'/offline-check/'+slot},localStorage,Blob,URL:{createObjectURL:b=>{const id='blob:'+urls.size;urls.set(id,b);return id;},revokeObjectURL(){}},setTimeout:()=>0,console};
 vm.createContext(context);
 const instrumented=code.replace(/\}\)\(\);\s*$/,`window.__test={getState:()=>state,payload,validateState,valueOf,progress,reasons,select,dims,records,draw};})();`);
 ok(instrumented!==code,'instrumentation hook');vm.runInContext(instrumented,context,{timeout:10000});
 return {html,data,doc,storage,downloads,t:window.__test,el:id=>doc.getElementById(id),set:(id,value)=>{const e=doc.getElementById(id);e.value=value;(e.oninput||e.onchange)?.();},check:id=>{const e=doc.getElementById(id);e.checked=true;e.onchange();}};
}
function fill(h){h.set('reviewerName','QA_ONLY');for(const d of h.t.dims)h.set('v-'+d.key,d.kind==='score'?'4':'0');for(const k of ['request','questions','output'])h.check('c-'+k);}
(async()=>{
for(const slot of [1,2]){
 const h=harness(slot),original=JSON.parse(fs.readFileSync(path.join(root,`reviewer_${slot}_packet.json`)));
 ok(!/[\u3400-\u9fff]/.test(h.html),'English form has no CJK text');
 ok(h.html.includes('<html lang="en">'),'document language is English');
 ok(JSON.stringify(h.data.packet)===JSON.stringify(original),'embedded packet unchanged');
 ok(h.t.progress().confirmed===0,'blank initial state');ok(h.t.payload().records.every(r=>Object.values(r.ratings).every(v=>v===null)),'all initial ratings null');
 ok(h.doc.getElementById('request').textContent===original.records[0].initial_request,'request intact');
 h.el('confirm').onclick();ok(h.t.progress().confirmed===0,'missing inputs cannot confirm');
 fill(h);h.el('confirm').onclick();let out=h.t.payload();
 ok(out.records[0].ratings.usefulness_1_to_5===4,'confirmed score exported');
 ok(out.records[0].ratings.unsupported_assumptions_count===0,'explicit zero exported');
 ok(out.review_form.progress.full===1,'full coverage counted');ok(h.el('reviewerName').readOnly,'identity locks after confirmation');
 h.el('exportJson').onclick();const exported=JSON.parse(await h.downloads.at(-1).blob.text());
 ok(exported.records.length===100&&exported.review_form_state.items,'backup includes drafts');
 h.set('notes','QA edit');ok(h.t.progress().confirmed===0,'edit invalidates');
 ok(!Object.values(h.t.getState().items[original.records[0].review_item_id].checks).some(Boolean),'read checks invalidated');
 ok(h.t.payload().records[0].ratings.usefulness_1_to_5===null,'draft excluded from formal ratings');
 h.check('u-coherence_1_to_5');h.set('notes','');for(const k of ['request','questions','output'])h.check('c-'+k);
 h.el('confirm').onclick();ok(h.t.progress().confirmed===0,'unjudgeable needs note');
 h.set('notes','Coherence cannot be judged from the available context.');h.el('confirm').onclick();
 out=h.t.payload();ok(out.records[0].ratings.coherence_1_to_5===null,'unable stays null');ok(out.review_form.progress.unresolved===1&&out.review_form.progress.full===0,'unresolved separately counted');
 h.t.select(original.records[1].review_item_id);h.set('v-usefulness_1_to_5','2');
 ok(h.t.payload().records[1].ratings.usefulness_1_to_5===null,'unconfirmed values withheld');
 const restored=harness(slot,{storage:h.storage});ok(restored.t.getState().current_id===original.records[1].review_item_id,'current position restored');ok(restored.t.progress().unresolved===1,'confirmation restored');ok(restored.t.getState().items[original.records[1].review_item_id].values.usefulness_1_to_5==='2','draft restored');
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(exported)}];await h.el('importFile').onchange();ok(h.t.progress().full===1,'import roundtrip');
 const legacy=JSON.parse(JSON.stringify(exported));
 const oldHash=h.data.compatible_source_packet_sha256[0];
 ok(/^[0-9a-f]{64}$/.test(oldHash),'original packet hash is recorded');
 legacy.review_form.source_packet_sha256=oldHash;
 legacy.review_form_state.source_packet_sha256=oldHash;
 delete legacy.review_form.interface_language;
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(legacy)}];await h.el('importFile').onchange();
 ok(h.t.progress().full===1&&!h.el('saveNotice').textContent.startsWith('Import failed'),'original-interface backup accepted');
 ok(h.t.getState().source_packet_sha256===h.data.source_packet_sha256,'imported state uses current packet hash');
 ok(h.t.payload().review_form.source_packet_sha256===h.data.source_packet_sha256,'re-export uses current packet hash');
 ok(h.t.payload().records[0].ratings.usefulness_1_to_5===4,'legacy import preserves confirmed rating');
 const unknown=JSON.parse(JSON.stringify(exported));
 unknown.review_form.source_packet_sha256='0'.repeat(64);
 unknown.review_form_state.source_packet_sha256='0'.repeat(64);
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(unknown)}];await h.el('importFile').onchange();
 ok(h.el('saveNotice').textContent.startsWith('Import failed'),'unknown packet fingerprint rejected');
 const legacyChanged=JSON.parse(JSON.stringify(legacy));legacyChanged.records[0].output={text:'Changed material'};
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(legacyChanged)}];await h.el('importFile').onchange();
 ok(h.el('saveNotice').textContent.startsWith('Import failed'),'changed legacy source rejected');
 const wrong=JSON.parse(JSON.stringify(exported));wrong.reviewer_slot=3-slot;
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(wrong)}];await h.el('importFile').onchange();ok(h.el('saveNotice').textContent.startsWith('Import failed'),'wrong reviewer rejected');ok(h.t.progress().full===1,'failed import preserves current state');
 const corrupt=JSON.parse(JSON.stringify(exported));corrupt.records[0].initial_request+=' changed';
 h.el('importFile').files=[{size:100,text:async()=>JSON.stringify(corrupt)}];await h.el('importFile').onchange();ok(h.el('saveNotice').textContent.startsWith('Import failed'),'changed source rejected');
 const invalid=JSON.parse(JSON.stringify(exported.review_form_state));invalid.items[original.records[0].review_item_id].values.unsupported_assumptions_count=' ';
 assert.throws(()=>h.t.validateState(invalid));checks++;
 const cases=['-1','1.5','1e2','Infinity','9007199254740992'];
 for(const value of cases){const s=JSON.parse(JSON.stringify(exported.review_form_state));s.items[original.records[0].review_item_id].values.unsupported_assumptions_count=value;assert.throws(()=>h.t.validateState(s));checks++;}
 h.el('exportCsv').onclick();const csv=await h.downloads.at(-1).blob.text();ok(csv.includes('"0"')&&csv.split('\r\n').length===101,'CSV has header +100 with zero');
 const declarations=h.t.payload().reviewer_declaration;ok(declarations.actual_blinding_confirmed===null&&declarations.reviewed_independently===null,'no automatic blinding assertion');
 // Verify every record can render without relying on private metadata or omitted output parts.
 for(const r of original.records){h.t.select(r.review_item_id);ok(h.el('request').textContent===r.initial_request,'all source requests rendered');if(r.domain==='study_planning')ok(h.el('output').children.some(e=>e.textContent===r.output.summary),'all plan summaries rendered');}
 ok(h.el('next').disabled,'last-record navigation bound');
 const failed=harness(slot,{storageFails:true});fill(failed);failed.el('confirm').onclick();ok(failed.t.progress().confirmed===1,'storage failure does not block review');failed.el('exportJson').onclick();ok(failed.downloads.length===1,'storage failure export available');
}
const report={status:'passed',assertions:checks,coverage:'Offline JavaScript logic and content tests using a minimal DOM stub. No browser rendering or native download/dialog behavior certified.',real_ratings_written:0,model_calls:0};
fs.writeFileSync(path.join(__dirname,'qa_logic.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
})().catch(e=>{console.error(e.stack);process.exit(1)});
