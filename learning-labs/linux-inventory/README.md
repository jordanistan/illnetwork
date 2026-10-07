# Independent Linux Lab: minimum local inventory

## Learning goal

Learn how to define and verify a narrow inventory boundary before administering a Linux system. This exercise records a small set of local facts while intentionally excluding user names, host names, IP addresses, process lists, environment variables, file contents, and credentials. OS and kernel labels can still be customized by an administrator, so inspect the report before sharing it.

## Setup and run

Use a Linux computer you own or a disposable Linux virtual machine. From the repository root:

```bash
python3 learning-labs/linux-inventory/run.py --output ./learning-lab-output/linux-inventory.json
```

The script uses only Python's standard library. It reads selected operating-system fields, basic platform information, root-filesystem capacity, and local TCP listener port numbers from Linux's `/proc` interface. It never opens a socket or sends a network request. It refuses to replace an existing output path.

## Expected outcome

The JSON report contains:

- a schema and exercise identifier;
- OS family/version, kernel release, architecture, and Python version;
- root-filesystem total and free byte counts; and
- unique local TCP listener port numbers, without addresses or process identities.

On a non-Linux system, the report still records portable platform information and marks Linux-only fields unavailable.

## Verify

Open the output and confirm that `excluded_fields` lists the identity and secret-bearing categories the exercise does not collect. Confirm `network_activity` is `none`.

Run the automated check:

```bash
python3 -m unittest discover -s learning-labs/tests -v
```

## Limits

This is not a vulnerability scan, compliance report, availability check, or proof that the system is secure. A list of listening port numbers lacks protocol ownership, exposure, firewall, and service-health context. Treat even sanitized system metadata as private unless you deliberately choose to share it.

## Cleanup

Delete the report path you supplied when you no longer need the evidence:

```bash
rm ./learning-lab-output/linux-inventory.json
```
