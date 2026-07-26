# VUE PACS ISO 27799 audit — real-deployment engagement

See `scope.md` first. This directory only ever holds documentation and
templates — the real configuration data and any resulting report are
generated locally and handed to the requester directly, never committed
here (see `.gitignore`).

## Running the assessment

1. Copy `pacs_iso27799_audit/sample_config.json` to a new file (e.g.
   `real_config.json` in this directory — already gitignored).
2. Fill in every field with the real deployment's real, current values.
   Only someone authorized to know/disclose this configuration should do
   this step.
3. Run the existing tools against it:

```bash
python -m pacs_iso27799_audit.audit --config vue-pacs-ichilov-audit/real_config.json \
    --output vue-pacs-ichilov-audit/real_report.md
python -m pacs_iso27799_audit.risk_model --config vue-pacs-ichilov-audit/real_config.json
```

Both commands only ever read that local JSON file — neither makes a
network connection.
