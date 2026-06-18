# Production (real clients)

This tree is the REAL-client counterpart of `testing/` and starts **empty**. No
mock/synthetic data ever goes here.

```
production/
├── corpus/        # real clients' AML policy PDFs (if you keep a shared copy)
├── inputs/        # real ingest payloads (normally come live via the API, not files)
└── clients/       # one folder per REAL client — real eval lives here
    └── client_1/  # (first real client — mirror testing/clients/client_0 structure)
        ├── policy.pdf
        ├── config.json     # their rule_to_section answer key (their section numbers)
        └── alerts/*.json
```

## Evaluate real clients
```bash
python eval/ir_metrics.py --prod            # all real clients
python eval/ir_metrics.py client_1 --prod   # one real client
```

The dummy/test client (`client_0`) and the synthetic policy stay in `testing/`
and never mix with this tree. Wipe mock data with `python scripts/reset.py --barebone`.
