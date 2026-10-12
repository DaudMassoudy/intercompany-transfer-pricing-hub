import { test, expect, Page } from '@playwright/test';

async function loginAdmin(page: Page) {
  await page.addInitScript(() => localStorage.setItem('otp_language', 'en'));
  await page.goto('/login');
  const inputs = page.locator('input');
  await inputs.nth(0).fill('demo.admin@otp.local');
  await inputs.nth(1).fill('Demo-OTP-2026!');
  await page.locator('button.btn').filter({ hasText: /Sign in|Anmelden/ }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
  await expect(page.locator('h1')).toBeVisible();
}

test.describe('15-layer UI practicality qualification', () => {
  test.beforeEach(async ({ page }) => { await loginAdmin(page); });

  const layers = [
    ['Master Data', '/master-data', /Enterprise Master Data Catalog|Enterprise-Stammdatenkatalog/, /New|Neu/],
    ['Allocation', '/allocations', /Allocation Workbench|Umlage-Workbench/, /New allocation rule|Neue Umlageregel/],
    ['Benchmarks', '/benchmarks', /Benchmark Management/, /Comparable|Comparables/],
    ['Segmented P&L', '/pnl', /Segmented P&L Workbench/, /P&L|GuV/],
    ['True-Ups', '/true-ups', /True-Up Workbench/, /Calculate true-up|True-up|True-Up/],
    ['Accounting', '/journals', /Accounting Journals|Buchungsjournale/, /Journal|Journale/],
    ['Exceptions', '/exceptions', /Exception Management/, /Exception|Ausnahme/],
    ['Documents / Evidence', '/documents', /Documents & Evidence/, /Upload|Document|Evidence/],
    ['Audit', '/audit', /Audit Trail|Prüfpfad/, /Audit|Event|Ereignis/],
    ['Approvals', '/workflows', /Workflow & Approval Center/, /approval|Approval|Workflow/],
    ['Policies', '/policies', /TP Policy Workbench/, /New policy|Policy/],
    ['Variance', '/variance', /Deterministic Variance Analysis|Deterministische Abweichungsanalyse/, /Run variance analysis|Abweichungsanalyse/],
    ['Reconciliation', '/reconciliation', /Reconciliation Control Center/, /Reconciliation|reconciliation/],
    ['Security', '/security', /Security Administration/, /Create service account|Service account/],
    ['Qualification', '/qualification', /Qualification Center/, /Synchronize release evidence|Qualification/]
  ] as const;

  for (const [layer, route, title, action] of layers) {
    test(`${layer}: workbench renders with an operator action`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator('h1')).toHaveText(title);
      await expect(page.locator('body')).toContainText(action);
      await expect(page.locator('body')).not.toContainText('Application error');
      await expect(page.locator('body')).not.toContainText('Internal Server Error');
    });
  }

  test('Qualification UI can synchronize real release evidence', async ({ page }) => {
    await page.goto('/qualification');
    const button=page.getByRole('button',{name:/Synchronize release evidence/i});
    await expect(button).toBeVisible();
    await button.click();
    await expect(page.locator('body')).toContainText(/Evidence synchronized for 2\.4\.0-rc\.3-hotfix7/i);

    // Final runtime evidence is produced after this browser suite. At this point,
    // verify the current release was synchronized and static release gates are PASS.
    const currentReleaseRows=page.locator('tr').filter({hasText:'2.4.0-rc.3-hotfix7'});
    await expect(currentReleaseRows.first()).toBeVisible();
    await expect(currentReleaseRows.filter({hasText:'RELEASE_INTEGRITY'})).toContainText('PASS');
    await expect(currentReleaseRows.filter({hasText:'MIGRATION_VALIDATION'})).toContainText('PASS');
  });

  test('Security UI creates and revokes a scoped one-time service credential', async ({ page }) => {
    await page.goto('/security');
    const suffix=Date.now().toString().slice(-8);
    const accountCode=page.getByLabel('Account code');
    await expect(accountCode).toBeVisible();
    await expect(accountCode).toBeEnabled({timeout:20_000});
    await accountCode.fill(`Q10-${suffix}`);
    // Hotfix 7 replaced free-text security scopes with governed selectors. Exercise
    // the current UI rather than the pre-Hotfix-7 comma-separated inputs.
    const readPermission=page.getByRole('checkbox',{name:'read'});
    if(!(await readPermission.isChecked())) await readPermission.check();
    await page.getByLabel('Authorized entities').selectOption(['DE01']);
    await page.getByRole('button',{name:'Create governed account'}).click();
    await expect(page.locator('body')).toContainText('One-time token');
    await expect(page.locator('.code')).toContainText('otp_sa_');
    const row=page.locator('tr').filter({hasText:`Q10-${suffix}`});
    await expect(row).toBeVisible();
    await row.getByRole('button',{name:'Revoke'}).click();
    await expect(row).toContainText(/REVOKED|INACTIVE/);
  });
});
