# Intelligent Learning Lab: human-review gate

## Learning goal

Learn to test an automated decision boundary before connecting it to an AI model or real data. The exercise applies a transparent policy to synthetic cases and checks whether a fictional automation candidate sends uncertain, sensitive, or stopped work to the right place.

## Setup and run

From the repository root:

```bash
python3 learning-labs/intelligent-review-gate/run.py --output ./learning-lab-output/review-gate.json
```

No model, API, account, or network connection is used. The deterministic policy blocks an explicit stop request, requires human review for sensitive or low-confidence work, and approves only the remaining case. The script refuses to replace an existing output path.

## Expected outcome

The evidence report should show `PASS`. Four candidate decisions match policy. The deliberately unsafe `wrong-output` candidate says `APPROVE`, while policy requires `HUMAN_REVIEW`; the evaluator must detect exactly that mismatch.

## Verify

Read each case's inputs, policy decision, candidate decision, and match value. Then run:

```bash
python3 -m unittest discover -s learning-labs/tests -v
```

## Limits

This exercise tests a tiny, explicit rule set—not an AI model's accuracy, fairness, security, or fitness for a real decision. Confidence values are synthetic. A production workflow needs domain review, privacy analysis, monitoring, failure handling, and accountable human ownership before handling real data or consequences.

## Cleanup

Delete the generated evidence when finished:

```bash
rm ./learning-lab-output/review-gate.json
```
