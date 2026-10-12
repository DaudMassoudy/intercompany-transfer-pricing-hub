# Login UI — portfolio screenshot refinement

The login form is styled to match the October 12, 2026 local demo screenshot: 616 px maximum-width desktop panel, split heading and DE/EN control, readable input labels and flexible role/persona buttons. The language switch and persona buttons retain keyboard navigation and `aria-pressed`, and authentication errors are announced with `role=alert`.

## Security and scope

Persona selection uses existing synthetic demo passwords and is limited to the demo implementation. **This is not secure production login behavior.** Never expose this service to the public internet with demo accounts enabled. The underlying authentication API and business calculations have not been altered. This change does not claim production authorization hardening.

## Verification

- Review the screenshot in `docs/screenshots/login-demo-personas.png` (captured from an earlier local run).
- After a fresh Docker build, manually test desktop/mobile layouts, English/German toggling, login and role selection.
- Runtime Docker/TypeScript test results are not represented by the screenshot.
