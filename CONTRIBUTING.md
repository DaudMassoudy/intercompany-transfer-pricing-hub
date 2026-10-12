# Contributing

This is a portfolio demonstration based on a release-candidate codebase. Please open an issue before substantial changes.

## Local checks

```bash
python -m compileall -q backend/app
cd backend && python -m pytest tests -q
cd ../frontend && npm install && npm run build
```

Dependencies must be installed first. Test and build success are not guaranteed in all environments. Do not commit credentials or real financial records.
