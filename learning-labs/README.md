# ill.network learning labs

These starter labs turn the **Independent Linux Lab**, **Infrastructure Learning Lab**, and **Intelligent Learning Lab** tracks into small, reproducible exercises. They are educational exercises, not production assessments or security scans.

Every lab:

- runs locally with Python 3.10 or newer and the standard library;
- uses only the current machine or synthetic data;
- requires no account, credential, network request, package install, or elevated privilege;
- writes its evidence only to a path you choose; and
- documents expected results, limits, and cleanup.

## Run all three

From the repository root:

```bash
python3 learning-labs/linux-inventory/run.py --output ./learning-lab-output/linux-inventory.json
python3 learning-labs/infrastructure-restore/run.py --workspace /tmp/ill-lab-restore
python3 learning-labs/intelligent-review-gate/run.py --output ./learning-lab-output/review-gate.json
```

Then run the verification suite:

```bash
python3 -m unittest discover -s learning-labs/tests -v
```

Each exercise has its own guide:

- [Independent Linux Lab](linux-inventory/README.md) — build a deliberately limited local inventory without collecting identity, process, address, or secret data.
- [Infrastructure Learning Lab](infrastructure-restore/README.md) — create, archive, restore, and verify a synthetic dataset.
- [Intelligent Learning Lab](intelligent-review-gate/README.md) — evaluate a deterministic human-review gate against synthetic edge cases.

## Safety boundary

Use these exercises only on a computer you own or are authorized to administer. The Linux lab observes the machine where it runs; it does not connect to another host. The other labs use synthetic inputs. Do not add real customer, employee, medical, credential, or production data to the exercises or commit generated reports.

Illnet Rx remains a separate, unreleased product in this repository. These labs do not invoke or alter its scanner, runtime, downloads, reports, or setup flow.
