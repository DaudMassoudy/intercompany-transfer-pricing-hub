import { test, expect, APIRequestContext } from '@playwright/test';
import fs from 'fs';
const AdmZip = require('adm-zip');

const API = process.env.API_URL || 'http://127.0.0.1:8000/api/v1';
const suffix = Date.now().toString().slice(-9);

type Tokens = Record<string,string>;
let tokens: Tokens = {};
let benchmarkCode='';
let workflowCode='';
let policyId=0;
let allocationRuleId=0;
let pnlRunId=0;
let adjustmentId=0;
let journalId=0;
let reconciliationId=0;
let autoExceptionId=0;

async function login(req:APIRequestContext,email:string,password:string){
  const r=await req.post(`${API}/auth/login`,{form:{username:email,password}});
  expect(r.ok(),`login ${email}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}
function h(token:string){return {Authorization:`Bearer ${token}`};}
const API_TIMEOUT_MS = 30_000;
const DATA_OPERATION_TIMEOUT_MS = 180_000;

async function json(req:APIRequestContext,method:string,path:string,token:string,data?:any,timeoutMs:number=API_TIMEOUT_MS){
  const options:any={headers:h(token),timeout:timeoutMs};
  if(data!==undefined) options.data=data;
  const r=await (req as any)[method.toLowerCase()](`${API}${path}`,options);
  const raw=await r.text();
  expect(r.ok(),`${method} ${path}: ${r.status()} ${raw}`).toBeTruthy();
  return raw?JSON.parse(raw):null;
}
async function governedCreate(req:APIRequestContext,domain:string,payload:any){
  const draft=await json(req,'POST',`/master-data/catalog/${domain}/changes`,tokens.steward,{change_type:'CREATE',payload,reason:'10/10 local qualification'});
  await json(req,'POST',`/master-data/catalog-changes/${draft.id}/submit`,tokens.steward);
  const approved=await json(req,'POST',`/master-data/catalog-changes/${draft.id}/approve`,tokens.manager);
  return approved.record;
}
async function approveAdjustment(req:APIRequestContext,id:number){
  await json(req,'POST',`/adjustments/${id}/submit`,tokens.analyst);
  let current=await json(req,'GET','/adjustments',tokens.analyst);
  let row=current.find((x:any)=>x.id===id);
  const roleTokens:Record<string,string>={TP_MANAGER:tokens.manager,FINANCE_CONTROLLER:tokens.finance,GROUP_TAX_DIRECTOR:tokens.director,HEAD_OF_TP:tokens.director};
  while(row && row.approval_status==='PENDING'){
    const step=row.steps.find((s:any)=>s.step_order===row.current_step);
    expect(step,`current approval step for adjustment ${id}`).toBeTruthy();
    await json(req,'POST',`/adjustments/${id}/approve`,roleTokens[step.required_role]||tokens.admin,{comments:'10/10 local qualification approval'});
    current=await json(req,'GET','/adjustments',tokens.analyst);
    row=current.find((x:any)=>x.id===id);
  }
  expect(row.status).toBe('APPROVED');
  return row;
}

test.describe.serial('15-layer live API qualification',()=>{
  test.beforeAll(async({request})=>{
    tokens.analyst=await login(request,'analyst@otp.local','Demo-Analyst-2026!');
    tokens.manager=await login(request,'manager@otp.local','Demo-Manager-2026!');
    tokens.finance=await login(request,'finance@otp.local','Demo-Finance-2026!');
    tokens.director=await login(request,'tax.director@otp.local','Demo-Director-2026!');
    tokens.steward=await login(request,'data.steward@otp.local','Demo-DataSteward-2026!');
    tokens.admin=await login(request,'demo.admin@otp.local','Demo-OTP-2026!');
    // Keep repeated qualification runs idempotent: remove only stale allocation rules
    // created by earlier Q10 qualification attempts. Business/demo rules are untouched.
    const activeRules=await json(request,'GET','/allocations/rules?status=ACTIVE',tokens.manager);
    for(const rule of activeRules.filter((x:any)=>String(x.rule_code||'').startsWith('Q10AL'))){
      await json(request,'POST',`/allocations/rules/${rule.id}/deactivate`,tokens.manager);
    }
  });

  test('Master Data — governed create, maker-checker, version and impact',async({request})=>{
    const code=`Q10TX${suffix}`;
    const rec=await governedCreate(request,'TRANSACTION_TYPES',{record_code:code,name:'10/10 Qualification Transaction',effective_from:'2026-01-01',attributes:{function:'QUALIFICATION',description:'Created by local runtime qualification'}});
    expect(rec.record_code).toBe(code);
    expect(rec.version_no).toBeGreaterThanOrEqual(1);
    const hist=await json(request,'GET',`/master-data/catalog/TRANSACTION_TYPES/${code}/history`,tokens.manager);
    expect(hist.length).toBeGreaterThan(0);
    const impact=await json(request,'GET',`/master-data/catalog/TRANSACTION_TYPES/${code}/impact`,tokens.manager);
    expect(impact).toBeTruthy();
  });

  test('Benchmarks — comparable observations, deterministic quartiles and governed refresh',async({request})=>{
    benchmarkCode=`Q10BM${suffix}`;
    const rec=await governedCreate(request,'BENCHMARKS',{record_code:benchmarkCode,name:'10/10 Runtime Benchmark',effective_from:'2026-01-01',attributes:{method:'TNMM',pli:'ROS',q1:'0.025',median:'0.035',q3:'0.045',tested_party:'DE01',geography:'DE',industry:'Distribution',search_period:'2026',financial_period:'2023-2025',source:'LOCAL_QUALIFICATION',database:'Runtime test dataset',screening_date:'2026-09-24',valid_until:'2027-12-31',refresh_date:'2027-09-01'}});
    expect(rec.record_code).toBe(benchmarkCode);
    const plis=[0.02,0.03,0.04,0.05];
    for(let i=0;i<plis.length;i++){
      const comp=await json(request,'POST',`/benchmarks/${benchmarkCode}/comparables`,tokens.admin,{company_name:`Q10 Comparable ${i+1} ${suffix}`,country:'DE',industry:'Distribution',status:'ACCEPTED',screening_reason:'Comparable accepted for runtime qualification'});
      await json(request,'POST',`/benchmarks/comparables/${comp.id}/observations`,tokens.admin,{fiscal_year:2025,sales:10000000+i*1000000,ebit:500000+i*10000,cost_base:9000000,assets:5000000,pli:plis[i],source_reference:'10/10 qualification'});
    }
    const stats=await json(request,'GET',`/benchmarks/${benchmarkCode}/statistics`,tokens.admin);
    expect(stats.comparable_count).toBe(4);
    expect(stats.q1).toBeLessThanOrEqual(stats.median);
    expect(stats.median).toBeLessThanOrEqual(stats.q3);
    const staged=await json(request,'POST',`/benchmarks/${benchmarkCode}/statistics/stage`,tokens.steward);
    expect(staged.request_code).toBeTruthy();
    const pending=await json(request,'GET',`/master-data/catalog-changes?domain=BENCHMARKS&status=DRAFT`,tokens.manager);
    const update=pending.find((x:any)=>x.request_code===staged.request_code);
    expect(update).toBeTruthy();
    await json(request,'POST',`/master-data/catalog-changes/${update.id}/submit`,tokens.steward);
    await json(request,'POST',`/master-data/catalog-changes/${update.id}/approve`,tokens.manager);
  });

  test('Policies — editable versioned lifecycle with approved benchmark linkage',async({request})=>{
    const code=`Q10POL${suffix}`;
    const p=await json(request,'POST','/policies/workbench',tokens.director,{policy_code:code,entity_code:'DE01',transaction_type:'DISTRIBUTION',tested_party_code:'DE01',counterparty_code:'TP-NL01',method:'TNMM',pli:'ROS',target:0.035,lower_bound:0.025,median:0.035,upper_bound:0.045,benchmark_id:benchmarkCode,effective_from:'2026-01-01',true_up_frequency:'QUARTERLY',materiality_threshold:50000,tolerance:0.0001,currency:'EUR',journal_template_code:'JT-TP-DEFAULT',notes:'10/10 runtime qualification policy'});
    policyId=p.id;
    await json(request,'POST',`/policies/${policyId}/submit`,tokens.director);
    await json(request,'POST',`/policies/${policyId}/approve`,tokens.manager);
    const active=await json(request,'POST',`/policies/${policyId}/activate`,tokens.director);
    expect(active.status).toBe('ACTIVE');
    const hist=await json(request,'GET',`/policies/${code}/history`,tokens.analyst);
    expect(hist.length).toBeGreaterThanOrEqual(1);
    const impact=await json(request,'GET',`/policies/${policyId}/impact`,tokens.analyst);
    expect(impact.historic_integrity).toContain('retain');
  });

  test('Allocation — arbitrary multi-stage execution, exclusions, benefit test, markup, FX and zero residual',async({request})=>{
    const code=`Q10AL${suffix}`;
    const rule=await json(request,'POST','/allocations/rules',tokens.analyst,{rule_code:code,sender_segment:'SHARED_SERVICES',cost_pool_name:'10/10 Global IT Pool',cost_pool_type:'IT',sender_entity_code:'NL02',period_scope:'MONTHLY',currency:'EUR',source_amount_source:'MANUAL_CONTROLLED',manual_amount_allowed:true,driver_type:'CUSTOM',driver_source:'MANUAL_CONTROLLED',recipients:{},exclusions:[{code:'SHAREHOLDER',reason:'Shareholder activities'}],stages:[{code:'REGION'},{code:'ENTITY'}],recipient_rules:{DE01:{eligible:true,benefit_test_required:true,benefit_test_passed:true,currency:'EUR'},FR01:{eligible:true,benefit_test_required:true,benefit_test_passed:true,currency:'EUR'}},markup_treatment:'CUSTOM_MARKUP',markup_rate:0.05,fx_methodology:'GROUP_MONTHLY_AVERAGE',fx_version:'2026-09',effective_from:'2026-01-01'});
    allocationRuleId=rule.id;
    const body={period:'2026-09',source_amount:8000000,stage_driver_values:{REGION:{SOURCE:{EU:100}},ENTITY:{EU:{DE01:60,FR01:40}}},exclusion_amounts:{SHAREHOLDER:500000}};
    const sim=await json(request,'POST',`/allocations/rules/${rule.id}/simulate`,tokens.analyst,body);
    expect(sim.reconciled).toBeTruthy(); expect(Math.abs(sim.residual)).toBeLessThanOrEqual(0.01); expect(sim.results.length).toBe(2);
    await json(request,'POST',`/allocations/rules/${rule.id}/submit`,tokens.analyst);
    await json(request,'POST',`/allocations/rules/${rule.id}/approve`,tokens.manager);
    await json(request,'POST',`/allocations/rules/${rule.id}/activate`,tokens.manager);
    const run=await json(request,'POST',`/allocations/rules/${rule.id}/execute`,tokens.analyst,body);
    expect(run.status).toBe('COMPLETED'); expect(Math.abs(run.residual)).toBeLessThanOrEqual(0.01); expect(run.total_recipient_charge).toBeGreaterThan(run.allocated_amount);
  });

  test('Segmented P&L — live import, mapping, authoritative build, cube, snapshot and lock',async({request})=>{
    test.setTimeout(300_000);
    const path='/qualification/sample_data/07_ERP_GL_Actuals.xlsx';
    expect(fs.existsSync(path),`sample file ${path}`).toBeTruthy();
    const r=await request.post(`${API}/imports`,{headers:h(tokens.analyst),timeout:DATA_OPERATION_TIMEOUT_MS,multipart:{source_system:'LOCAL_QUALIFICATION',period:'2026-09',file:{name:'07_ERP_GL_Actuals.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:fs.readFileSync(path)}}});
    const txt=await r.text();
    let imp:any;
    if(r.status()===409){
      // Qualification is deliberately rerunnable against an already-qualified runtime.
      // Preserve the production duplicate-import control and reuse the exact previously
      // validated source batch instead of weakening the API or forcing a duplicate.
      const conflict=JSON.parse(txt);
      const existingCode=conflict?.detail?.existing_import_code;
      expect(existingCode,`duplicate response must identify reusable import: ${txt}`).toBeTruthy();
      const imports=await json(request,'GET','/imports?limit=500',tokens.analyst);
      const existing=imports.find((x:any)=>x.import_code===existingCode);
      expect(existing,`existing qualification import ${existingCode} must be retrievable`).toBeTruthy();
      imp={...existing,import_id:existing.id};
    }else{
      expect(r.ok(),`import: ${r.status()} ${txt}`).toBeTruthy();
      imp=JSON.parse(txt);
    }
    expect(imp.accepted_rows).toBeGreaterThan(0);
    const mapped=await json(request,'POST',`/mappings/run?import_id=${imp.import_id}`,tokens.analyst,undefined,DATA_OPERATION_TIMEOUT_MS);
    expect(mapped.mapped).toBeGreaterThan(0);
    // The authoritative P&L control requires a completed run for every active allocation
    // methodology. The seeded demo rule is intentionally active, so create its controlled
    // September run when one is not already present. This preserves the control instead of
    // weakening the backend merely to make qualification pass.
    const allocationRuns=await json(request,'GET','/allocations/runs',tokens.analyst);
    const seedRunExists=allocationRuns.some((x:any)=>x.rule_code==='ALLOC-HQ-IT-001' && x.period==='2026-09' && x.status==='COMPLETED');
    if(!seedRunExists){
      const seedRules=await json(request,'GET','/allocations/rules?status=ACTIVE',tokens.analyst);
      const seedRule=seedRules.find((x:any)=>x.rule_code==='ALLOC-HQ-IT-001');
      if(seedRule){
        const drivers=seedRule.recipients && Object.keys(seedRule.recipients).length ? seedRule.recipients : {'DE01-DIST':450,'FR01-DIST':300,'IT01-DIST':250};
        await json(request,'POST','/allocations/run',tokens.analyst,{rule_code:seedRule.rule_code,period:'2026-09',source_amount:1000000,driver_values:drivers});
      }
    }
    const pnl=await json(request,'POST','/pnl/build',tokens.analyst,{as_of_period:'2026-09',import_ids:[imp.import_id],publish:true},DATA_OPERATION_TIMEOUT_MS);
    pnlRunId=pnl.run_id; expect(pnlRunId).toBeTruthy();
    const cube=await json(request,'GET',`/pnl/runs/${pnlRunId}/cube?dimensions=entity,segment,transaction,currency`,tokens.analyst);
    expect(cube.rows.length).toBeGreaterThan(0); expect(cube.source_hash).toBeTruthy();
    const snap=await json(request,'POST',`/pnl/runs/${pnlRunId}/snapshots`,tokens.analyst,{scenario:'ACTUAL',label:'10/10 Runtime Snapshot',comment:'Local qualification'});
    const locked=await json(request,'POST',`/pnl/snapshots/${snap.id}/lock`,tokens.manager);
    expect(locked.status).toBe('LOCKED');
  });

  test('Variance — deterministic additive bridge mathematically reconciles',async({request})=>{
    const v=await json(request,'POST','/variance/run',tokens.analyst,{entity_code:'DE01',actual_period:'2026-09',baseline_type:'BUDGET'});
    expect(Math.abs(v.residual)).toBeLessThanOrEqual(0.01);
    expect(Math.abs(v.component_total-v.ebit_variance)).toBeLessThanOrEqual(0.01);
    expect(v.components.length).toBeGreaterThan(0);
  });

  test('Approvals — user-configured workflow, maker-checker and multi-role sequential completion',async({request})=>{
    workflowCode=`Q10WF${suffix}`;
    await governedCreate(request,'WORKFLOW_DEFINITIONS',{record_code:workflowCode,name:'10/10 Runtime Approval',effective_from:'2026-01-01',attributes:{object_type:'TRUE_UP',min_amount:'0',approval_mode:'SEQUENTIAL',approver_roles:'TP_MANAGER,FINANCE_CONTROLLER,GROUP_TAX_DIRECTOR',sla_hours:48,escalation_role:'GROUP_TAX_DIRECTOR',allow_delegation:true,prevent_self_approval:true}});
    const inst=await json(request,'POST','/workflow-engine/instances',tokens.analyst,{workflow_code:workflowCode,object_type:'TRUE_UP',object_id:`Q10-OBJ-${suffix}`,amount:1000000,materiality:50000,entity_code:'DE01',country:'DE',method:'TNMM',risk:'HIGH'});
    expect(inst.tasks.length).toBe(3);
    const creatorAttempt=await request.post(`${API}/workflow-engine/tasks/${inst.tasks[0].id}/approve`,{headers:h(tokens.analyst),data:{comments:'must fail'}});
    expect([403,409]).toContain(creatorAttempt.status());
    await json(request,'POST',`/workflow-engine/tasks/${inst.tasks[0].id}/approve`,tokens.manager,{comments:'TP Manager approved'});
    await json(request,'POST',`/workflow-engine/tasks/${inst.tasks[1].id}/approve`,tokens.finance,{comments:'Finance approved'});
    await json(request,'POST',`/workflow-engine/tasks/${inst.tasks[2].id}/approve`,tokens.director,{comments:'Tax Director approved'});
    const instances=await json(request,'GET','/workflow-engine/instances',tokens.analyst);
    expect(instances.find((x:any)=>x.id===inst.id).status).toBe('APPROVED');
  });

  test('True-Ups — deterministic target adjustment and complete maker-checker approval',async({request})=>{
    const calcs=await json(request,'GET','/calculations?entity_code=DE01',tokens.analyst);
    expect(calcs.length).toBeGreaterThan(0);
    const tu=await json(request,'POST','/true-ups',tokens.analyst,{calculation_id:calcs[0].id,target_type:'POLICY_TARGET',frequency:'QUARTERLY',reason:'10/10 local qualification'});
    adjustmentId=tu.id; expect(Math.abs(tu.amount)).toBeGreaterThan(0);
    const approved=await approveAdjustment(request,adjustmentId);
    expect(approved.status).toBe('APPROVED');
  });

  test('Accounting — template-driven balanced journal and idempotent ERP simulator posting',async({request})=>{
    const journal=await json(request,'POST',`/journals/from-adjustment/${adjustmentId}?template_code=JT-TP-DEFAULT`,tokens.finance);
    journalId=journal.journal_id; expect(journal.balanced).toBeTruthy(); expect(journal.debit_total).toBe(journal.credit_total); expect(journal.template_code).toBe('JT-TP-DEFAULT');
    const posted=await json(request,'POST',`/postings/simulate/${journalId}`,tokens.finance);
    expect(['POSTED','RECONCILED']).toContain(posted.status); expect(posted.simulated).toBeTruthy(); reconciliationId=posted.reconciliation.id;
    const replay=await json(request,'POST',`/postings/simulate/${journalId}`,tokens.finance);
    expect(replay.idempotent_replay).toBeTruthy();
  });

  test('Reconciliation — stage rebuild, zero-difference control and certification',async({request})=>{
    const rebuilt=await json(request,'POST',`/reconciliations/${reconciliationId}/stages/rebuild`,tokens.finance);
    expect(rebuilt.status).toBe('RECONCILED'); expect(rebuilt.stages.length).toBe(3); for(const s of rebuilt.stages) expect(Math.abs(s.difference)).toBeLessThanOrEqual(0.01);
    const cert=await json(request,'POST',`/reconciliations/${reconciliationId}/certify`,tokens.manager,{comment:'10/10 local qualification certification'});
    expect(cert.status).toBe('CERTIFIED'); expect(cert.certified_by).toBeTruthy();
  });

  test('Exceptions — automatic reconciliation exception plus remediation and waiver controls',async({request})=>{
    const calcs=await json(request,'GET','/calculations?entity_code=DE01',tokens.analyst);
    const tu=await json(request,'POST','/true-ups',tokens.analyst,{calculation_id:calcs[0].id,target_type:'POLICY_TARGET',frequency:'AD_HOC',reason:'10/10 exception path'});
    await approveAdjustment(request,tu.id);
    const j=await json(request,'POST',`/journals/from-adjustment/${tu.id}?template_code=JT-TP-DEFAULT`,tokens.finance);
    const p=await json(request,'POST',`/postings/simulate/${j.journal_id}?simulate_posting_delta=10`,tokens.finance);
    expect(p.reconciliation.status).toBe('DIFFERENCE'); expect(p.reconciliation.exception_code).toBeTruthy();
    const list=await json(request,'GET','/exceptions',tokens.analyst);
    const exc=list.find((x:any)=>x.exception_code===p.reconciliation.exception_code); expect(exc).toBeTruthy(); autoExceptionId=exc.id;
    const triaged=await json(request,'POST',`/exceptions/${autoExceptionId}/triage`,tokens.analyst,{root_cause:'Qualification posting delta',remediation:'Investigate and correct posting amount',comment:'Runtime generated exception',attachment:'qualification://posting-delta'});
    expect(triaged.status).toBe('IN_PROGRESS');
    const waived=await json(request,'POST',`/exceptions/${autoExceptionId}/waive`,tokens.manager,{waiver_reason:'Intentional 10/10 qualification difference'});
    expect(waived.status).toBe('WAIVED');
  });

  test('Documents / Evidence — versioned upload, evidence search and complete adjustment evidence pack',async({request})=>{
    const phrase=`Q10-EVIDENCE-${suffix}`;
    const r=await request.post(`${API}/documents/upload`,{headers:h(tokens.analyst),multipart:{document_code:`Q10DOC${suffix}`,document_type:'CALCULATION_EVIDENCE',entity_code:'DE01',period:'2026-09',access_classification:'CONFIDENTIAL',tags:'qualification,true-up',linked_object_type:'ADJUSTMENT',linked_object_id:String(adjustmentId),file:{name:'qualification-evidence.txt',mimeType:'text/plain',buffer:Buffer.from(`${phrase}\nEvidence generated by the local 10/10 qualification suite.`)}}});
    const raw=await r.text(); expect(r.ok(),`document upload: ${r.status()} ${raw}`).toBeTruthy(); const doc=JSON.parse(raw); expect(doc.sha256).toHaveLength(64);
    const hits=await json(request,'GET',`/documents/search/evidence?q=${encodeURIComponent(phrase)}`,tokens.analyst); expect(hits.some((x:any)=>x.document_id===doc.id)).toBeTruthy();
    const packResponse=await request.get(`${API}/evidence-packs/adjustments/${adjustmentId}`,{headers:h(tokens.analyst)});
    expect(packResponse.ok(),`evidence pack: ${packResponse.status()} ${await packResponse.text()}`).toBeTruthy();
    expect(packResponse.headers()['content-type']||'').toContain('application/zip');
    const packBytes=await packResponse.body();
    expect(packBytes.subarray(0,2).toString()).toBe('PK');
    const zip=new AdmZip(packBytes);
    const entryNames=zip.getEntries().map((e:any)=>e.entryName);
    expect(entryNames).toContain('evidence.json');
    expect(entryNames).toContain('manifest_final.json');
    const pack=JSON.parse(zip.readAsText('evidence.json'));
    expect(pack.adjustment.id).toBe(adjustmentId); expect(pack.policy).toBeTruthy(); expect(pack.journal).toBeTruthy(); expect(pack.reconciliation).toBeTruthy();
  });

  test('Audit — transaction-chain reconstruction contains the executed financial lifecycle',async({request})=>{
    const chain=await json(request,'GET','/audit/transaction-chain/DE01',tokens.analyst);
    expect(chain.event_count).toBeGreaterThan(0);
    const types=new Set(chain.events.map((x:any)=>x.event_type));
    for(const needed of ['TRUE_UP_CREATED','ADJUSTMENT_SUBMITTED','JOURNAL_CREATED','ERP_POSTING_SIMULATED']) expect(types.has(needed),`audit event ${needed}`).toBeTruthy();
  });

  test('Security — entity-scoped service token is enforced by backend and revocation is immediate',async({request})=>{
    const sa=await json(request,'POST','/security/service-accounts',tokens.admin,{account_code:`Q10SA${suffix}`,permissions:['read'],entity_codes:['DE01']});
    expect(sa.token).toContain('otp_sa_');
    const ok=await request.get(`${API}/entities/DE01`,{headers:h(sa.token)}); expect(ok.ok(),await ok.text()).toBeTruthy();
    const denied=await request.get(`${API}/entities/FR01`,{headers:h(sa.token)}); expect(denied.status()).toBe(403);
    await json(request,'POST',`/security/service-accounts/${sa.id}/revoke`,tokens.admin);
    const revoked=await request.get(`${API}/entities/DE01`,{headers:h(sa.token)}); expect(revoked.status()).toBe(401);
  });

  test('Qualification — evidence registry is synchronized without converting external gates into fake PASS',async({request})=>{
    const q=await json(request,'POST','/qualification/sync-release-evidence',tokens.admin);
    expect(q.release_version).toBe('2.4.0-rc.3-hotfix7');
    expect(q.controls.length).toBeGreaterThan(0);
    const center=await json(request,'GET','/qualification',tokens.admin);
    const external=center.controls.filter((x:any)=>x.control_type==='EXTERNAL');
    expect(external.length).toBeGreaterThan(0);
    expect(external.every((x:any)=>['EXTERNAL_REQUIRED','EXTERNAL QUALIFICATION REQUIRED','NOT RUN','PENDING'].includes(x.status))).toBeTruthy();
  });
});
