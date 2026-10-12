# Hotfix 7 Qualification Repair 3

## Symptom
The local qualification reached 31/32 passing tests. The remaining Security UI browser test could not locate the `Account code` form control with Playwright's accessible-label locator.

## Root cause
The Security Administration form rendered visual `<label>` elements as siblings of the input/select controls without `htmlFor`/`id` associations. The form looked correct to a sighted user, but the labels were not programmatically associated with their controls. Playwright correctly treated `getByLabel('Account code')` as unmatched.

## Repair
- Associated `Account code` with `service-account-code` using `label htmlFor` and `input id`.
- Associated `Authorized entities` with `service-account-entities` using `label htmlFor` and `select id`.
- No security permission, service-account lifecycle, API, database, or qualification scoring rule was weakened.

## Expected effect
The governed Security UI remains unchanged visually, becomes more accessible to assistive technology, and the existing Hotfix 7 qualification test can address the actual controls through their accessible labels.
