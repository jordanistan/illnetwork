# Infrastructure Learning Lab: synthetic restore drill

## Learning goal

Practice proving that an archive can be restored and verified. A backup that has never been restored is only an assumption.

## Setup and run

Choose a disposable workspace. The command creates a new, uniquely named run directory inside it and never deletes or replaces an existing file:

```bash
python3 learning-labs/infrastructure-restore/run.py --workspace /tmp/ill-lab-restore
```

The exercise creates three synthetic text files, records their SHA-256 digests, builds a ZIP archive, validates every archive member path, extracts into a separate directory, and compares restored digests to the originals.

## Expected outcome

The command prints the path to `outcome.json`. The report's `result` should be `PASS`, `archive_members_safe` should be `true`, and each item in `files` should have matching source and restored SHA-256 values.

## Verify

Review the JSON evidence, then run:

```bash
python3 -m unittest discover -s learning-labs/tests -v
```

## Limits

The drill proves integrity for a tiny synthetic dataset on one local filesystem. It does not test production permissions, encryption, retention, remote storage, disaster timing, databases, application consistency, or recovery objectives. Never substitute real production or customer data into this starter exercise.

## Cleanup

After reviewing the outcome, delete only the disposable workspace you selected:

```bash
rm -r /tmp/ill-lab-restore
```
