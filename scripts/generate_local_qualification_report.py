from __future__ import annotations
import json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'qualification'/'results'
DOCS=ROOT/'docs'
PW=RESULTS/'playwright.json'

LAYER_TESTS={
    'Master Data':['Master Data: workbench renders with an operator action','Master Data — governed create, maker-checker, version and impact'],
    'Allocation':['Allocation: workbench renders with an operator action','Allocation — arbitrary multi-stage execution, exclusions, benefit test, markup, FX and zero residual'],
    'Benchmarks':['Benchmarks: workbench renders with an operator action','Benchmarks — comparable observations, deterministic quartiles and governed refresh'],
    'Segmented P&L':['Segmented P&L: workbench renders with an operator action','Segmented P&L — live import, mapping, authoritative build, cube, snapshot and lock'],
    'True-Ups':['True-Ups: workbench renders with an operator action','True-Ups — deterministic target adjustment and complete maker-checker approval'],
    'Accounting':['Accounting: workbench renders with an operator action','Accounting — template-driven balanced journal and idempotent ERP simulator posting'],
    'Exceptions':['Exceptions: workbench renders with an operator action','Exceptions — automatic reconciliation exception plus remediation and waiver controls'],
    'Documents / Evidence':['Documents / Evidence: workbench renders with an operator action','Documents / Evidence — versioned upload, evidence search and complete adjustment evidence pack'],
    'Audit':['Audit: workbench renders with an operator action','Audit — transaction-chain reconstruction contains the executed financial lifecycle'],
    'Approvals':['Approvals: workbench renders with an operator action','Approvals — user-configured workflow, maker-checker and multi-role sequential completion'],
    'Policies':['Policies: workbench renders with an operator action','Policies — editable versioned lifecycle with approved benchmark linkage'],
    'Variance':['Variance: workbench renders with an operator action','Variance — deterministic additive bridge mathematically reconciles'],
    'Reconciliation':['Reconciliation: workbench renders with an operator action','Reconciliation — stage rebuild, zero-difference control and certification'],
    'Security':['Security: workbench renders with an operator action','Security — entity-scoped service token is enforced by backend and revocation is immediate','Security UI creates and revokes a scoped one-time service credential'],
    'Qualification':['Qualification: workbench renders with an operator action','Qualification — evidence registry is synchronized without converting external gates into fake PASS','Qualification UI can synchronize real release evidence'],
}

def status_file(name:str)->str:
    p=RESULTS/name
    return p.read_text(errors='ignore').strip().upper() if p.exists() else 'NOT RUN'

def walk_suites(suites, prefix=''):
    out=[]
    for s in suites or []:
        sp=(prefix+' '+s.get('title','')).strip()
        for spec in s.get('specs',[]):
            title=(sp+' '+spec.get('title','')).strip()
            results=[]
            for t in spec.get('tests',[]):
                for r in t.get('results',[]): results.append(r.get('status'))
            ok=bool(results) and all(x in {'passed','skipped'} for x in results) and any(x=='passed' for x in results)
            out.append((spec.get('title',''),title,'PASS' if ok else 'FAIL'))
        out.extend(walk_suites(s.get('suites',[]),sp))
    return out

if PW.exists():
    try: data=json.loads(PW.read_text(errors='ignore'))
    except Exception as exc:
        print(f'Could not parse {PW}: {exc}',file=sys.stderr);data={}
    specs=walk_suites(data.get('suites',[]))
else:
    specs=[]

def find_test(expected:str):
    matches=[s for s in specs if expected==s[0] or expected in s[1]]
    if not matches:return 'NOT RUN'
    return 'PASS' if all(m[2]=='PASS' for m in matches) else 'FAIL'

backend=status_file('backend-tests.status')
release=status_file('release-validation.status')
startup=status_file('runtime-startup.status')
frontend=status_file('frontend-runtime.status')

rows=[]
for layer,expected in LAYER_TESTS.items():
    checks=[find_test(x) for x in expected]
    mandatory=checks+[backend,release,startup,frontend]
    final='PASS' if all(x=='PASS' for x in mandatory) else ('FAIL' if 'FAIL' in mandatory else 'NOT RUN')
    score='10/10' if final=='PASS' else 'NOT QUALIFIED'
    rows.append((layer,score,final,checks))

overall='PASS' if all(r[2]=='PASS' for r in rows) else ('FAIL' if any(r[2]=='FAIL' for r in rows) else 'NOT RUN')
now=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')

lines=[
'# Local 10/10 Practicality Qualification — v2.4.0-rc.3-hotfix7','',
f'QUALIFICATION_STATUS: {overall}','',
f'Generated: {now}','',
'## Global runtime gates','',
'| Gate | Status |','|---|---|',
f'| Docker/application startup | **{startup}** |',
f'| Frontend runtime | **{frontend}** |',
f'| Backend regression suite | **{backend}** |',
f'| Release validation | **{release}** |','',
'## 15 target layers','',
'| Layer | Final practicality | Local qualification |','|---|---:|---|'
]
for layer,score,st,_ in rows:lines.append(f'| {layer} | **{score}** | **{st}** |')
lines += ['',f'**Overall local qualification: {overall}**','',
'10/10 is awarded here only when the layer-specific live API test, operator-facing browser test, backend regression suite, release validation and live runtime gates all pass on this machine. External customer/third-party certification is intentionally separate.','',
'## External qualification (not self-certified)','',
'- Live customer SAP / Oracle / Dynamics qualification','- Customer OIDC/SAML/Entra/Okta integration','- Independent penetration test','- Customer Finance / TP UAT sign-off','- Parallel production close','- Production DR / infrastructure sign-off','']

report='\n'.join(lines)
(RESULTS/'LOCAL_10_10_QUALIFICATION.md').write_text(report,encoding='utf-8')
(DOCS/'LOCAL_10_10_QUALIFICATION_RESULT.md').write_text(report,encoding='utf-8')

# Feed actual local execution evidence into the Qualification Center's report contract.
def write_status_doc(filename:str,title:str,status:str,body_lines:list[str]):
    content=[f'# {title}','',f'QUALIFICATION_STATUS: {status}','',*body_lines]
    (DOCS/filename).write_text('\n'.join(content).rstrip()+'\n',encoding='utf-8')

uat_body=[
    f'Local runtime execution: **{overall}**','',
    'The browser/API qualification suite executed the 15 target layers on the local Docker runtime.','',
    *lines[lines.index('## 15 target layers'):]
]
write_status_doc('UAT_RESULTS.md','UAT Results — v2.4.0-rc.3-hotfix7',overall,uat_body)

write_status_doc(
    'FRONTEND_TEST_REPORT.md',
    'Frontend Validation Report — v2.4.0-rc.3-hotfix7',
    overall,
    [
      f'- Docker production frontend build/startup: **{frontend}**',
      f'- Browser E2E target-layer suite: **{overall}**',
      '- Playwright evidence: `qualification/results/playwright.json`',
      '- Test artifacts on failure: `qualification/results/test-artifacts/`',
    ]
)

backend_text=(RESULTS/'backend-tests.txt').read_text(errors='ignore') if (RESULTS/'backend-tests.txt').exists() else ''
backend_tail='\n'.join(backend_text.splitlines()[-20:])
write_status_doc(
    'TEST_REPORT.md',
    'Test Report — Intercompany Transfer Pricing Hub v2.4.0-rc.3-hotfix7',
    backend,
    [
      f'- Local Docker backend regression status: **{backend}**',
      '- Raw execution evidence: `qualification/results/backend-tests.txt`',
      '- JUnit evidence: `qualification/results/backend-junit.xml`',
      '',
      '### Pytest execution tail',
      '```text', backend_tail, '```'
    ]
)

coverage_pct=None
coverage_path=RESULTS/'coverage-local.xml'
if coverage_path.exists():
    try:
        root_xml=ET.parse(coverage_path).getroot()
        coverage_pct=round(float(root_xml.attrib.get('line-rate','0'))*100,2)
    except Exception:
        coverage_pct=None
coverage_status='PASS' if coverage_pct is not None and backend=='PASS' else ('FAIL' if backend=='FAIL' else 'NOT RUN')
coverage_body=[
    f'- Measured local overall backend line coverage: **{coverage_pct:.2f}%**' if coverage_pct is not None else '- Measured local overall backend line coverage: **NOT AVAILABLE**',
    '- Raw XML evidence: `qualification/results/coverage-local.xml`',
    '- Coverage is reported transparently and is not inflated by excluding low-covered modules.',
    '- The 10/10 score in this report is a *practicality* qualification: each layer must also pass its own live browser/API business workflow.'
]
write_status_doc('COVERAGE_REPORT.md','Coverage Report — v2.4.0-rc.3-hotfix7',coverage_status,coverage_body)

release_text=(RESULTS/'release-validation.txt').read_text(errors='ignore') if (RESULTS/'release-validation.txt').exists() else ''
release_tail='\n'.join(release_text.splitlines()[-30:])
write_status_doc(
    'VALIDATION_REPORT.md',
    'Release Validation Report — v2.4.0-rc.3-hotfix7',
    release,
    [
      f'- Local release/package validation: **{release}**',
      '- Raw execution evidence: `qualification/results/release-validation.txt`',
      '',
      '### Validation execution tail',
      '```text', release_tail, '```'
    ]
)

security_row=next((r for r in rows if r[0]=='Security'),None)
security_status=security_row[2] if security_row else 'NOT RUN'
write_status_doc(
    'SECURITY_REPORT.md',
    'Security Validation Report — v2.4.0-rc.3-hotfix7',
    security_status,
    [
      f'- Local Security-layer practicality qualification: **{security_status}**',
      '- Live checks include backend-enforced entity scoping, one-time service credentials, and immediate revocation.',
      '- Independent penetration testing and customer IdP qualification remain EXTERNAL QUALIFICATION REQUIRED.'
    ]
)

print(report)
sys.exit(0 if overall=='PASS' else 1)
