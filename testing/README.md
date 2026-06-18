# Testing (mock environment)

All MOCK/synthetic data, fully **regeneratable** from code. Separate from
`production/` (real clients) so the two never mix.

```
testing/
├── build_policy.py      # generates the synthetic Aegis policy PDF
├── sources.md           # real Indian AML source URLs (reference)
├── corpus/              # the generated policy PDF
├── inputs/              # the demo ingest payload used by generation scripts
└── clients/
    └── client_0/        # the DUMMY test client (named 0 so real clients start at 1)
        ├── policy.pdf
        ├── config.json  # eval answer key (rule -> section in THIS policy)
        └── alerts/*.json
```

## Regenerate everything here
```bash
python scripts/seed_testing.py        # rebuild policy + inputs + client_0 from scratch
# or:
python scripts/reset.py --seed        # wipe runtime + regenerate testing/
```

## Wipe it
```bash
python scripts/reset.py --barebone    # delete all mock data (keeps build_policy.py + sources.md)
```

Everything under `corpus/`, `inputs/`, and `clients/` is produced by
`scripts/seed_testing.py`, so it is safe to delete and recreate at will.
