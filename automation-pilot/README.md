# ILLNET AI approval pilot

This is a deliberately small, offline demonstration of one automation control:
a workflow plan stays pending until a person records an explicit decision about
the exact hashed plan. Even an approval authorizes only a demo handoff. The tool
cannot send a message, call a model, use a network, schedule work, deploy code,
take payment, or authorize live execution.

The example data is synthetic. Do not substitute customer, employee, medical,
financial, access, credential, or other sensitive data. This is a control-flow
prototype, not an AI service or a claim that a production integration exists.

## Run the example

Use Python 3.10 or newer and an empty local workspace:

```bash
python3 automation-pilot/pilot.py prepare \
  --request automation-pilot/examples/request.json \
  --workspace /tmp/illnet-ai-demo \
  --output plan.json

python3 automation-pilot/pilot.py review \
  --request automation-pilot/examples/request.json \
  --workspace /tmp/illnet-ai-demo \
  --plan plan.json \
  --output review.json \
  --decision approve \
  --reviewer-label demo-reviewer \
  --reason "The synthetic output meets the documented demo criteria."

python3 automation-pilot/pilot.py verify \
  --request automation-pilot/examples/request.json \
  --workspace /tmp/illnet-ai-demo \
  --plan plan.json \
  --review review.json
```

Use `--decision reject` when the plan needs revision. The decision file records
the plan SHA-256, an unauthenticated reviewer label, reason, and a permanently false
`live_execution_authorized` field. `verify` fails if the plan changes afterward
or differs from the supplied request, or the decision/status fields disagree.
The label is not an identity proof or signature: anyone who can write the local
workspace can create a review. The hash provides integrity binding, not
authentication or non-repudiation.

The tool writes new files with owner-only permissions and refuses overwrites,
symlink workspaces/ancestors/members, absolute paths, traversal, hidden names,
and nested output paths. Input JSON has an exact schema, a 16 KiB limit,
approved workflow and output names, synthetic-only classification, bounded
text, and best-effort sensitive field/value rejection. The classification is
self-declared and the filter cannot prove that data is synthetic, secret-free,
or free of personal information; a human must inspect every input.

## Supported demo workflows

- `support_summary`
- `report_outline`
- `inquiry_draft`

All produce a deterministic plan, not the described business output. That keeps
the prototype inspectable and prevents a mock-up from being mistaken for a live
agent or connected service.

## Tests and cleanup

```bash
python3 -m unittest discover -s automation-pilot -p 'test_*.py' -v
rm -r /tmp/illnet-ai-demo
```

Review before deleting any non-demo directory. The repository Action runs only
the offline tests and the synthetic prepare/review/verify sequence.

## Production gate

Before any real integration, separately approve its data inventory, processor
and retention terms, minimum permissions, authentication, failure behavior,
human authority, audit storage, deletion, monitoring, rollback, service owner,
support path, and written acceptance tests. Re-run security/privacy review with
synthetic or formally authorized data. This pilot supplies none of those
approvals and must not be connected to a live account.
