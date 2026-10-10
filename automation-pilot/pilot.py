#!/usr/bin/env python3
"""Offline, synthetic-data workflow planning with an explicit human decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


MAX_FILE_BYTES = 64 * 1024
MAX_REQUEST_BYTES = 16 * 1024
REQUEST_KEYS = {
    "schema_version",
    "request_id",
    "workflow",
    "objective",
    "data_classification",
    "inputs",
    "allowed_outputs",
    "human_owner",
}
INPUT_KEYS = {"name", "value"}
WORKFLOWS = {
    "inquiry_draft": "Prepare a draft inquiry response for review",
    "report_outline": "Prepare a report outline for review",
    "support_summary": "Prepare a support summary for review",
}
OUTPUTS = {"draft_response", "report_outline", "review_checklist", "summary"}
PLAN_KEYS = {
    "schema_version",
    "request_id",
    "request_sha256",
    "status",
    "workflow",
    "objective",
    "human_owner",
    "allowed_outputs",
    "input_names",
    "steps",
    "capabilities",
    "decision_required",
}
REVIEW_KEYS = {
    "schema_version",
    "request_id",
    "plan_sha256",
    "decision",
    "status",
    "reviewer_label",
    "reason",
    "live_execution_authorized",
}
CAPABILITIES = {
    "customer_data": False,
    "external_actions": False,
    "model_calls": False,
    "network": False,
    "synthetic_data_only": True,
}
DECISION_NOTICE = (
    "approve or reject this exact plan; approval does not authorize live execution"
)
SIMPLE_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
PERSON_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}\Z")
FIELD_NAME = re.compile(r"[a-z][a-z0-9_]{1,39}\Z")
SENSITIVE_NAME = re.compile(
    r"(?:access[_-]?key|api[_-]?key|authorization|aws|bank|card|cookie|credential|"
    r"diagnos|email|financial|medical|password|patient|phone|private|secret|session|"
    r"ssn|token)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\bBearer\s+[A-Za-z0-9._~+/=-]{8,}|"
    r"\b(?:gh[oprsu]_|sk-)[A-Za-z0-9_-]{8,}|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
    r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|"
    r"\bxox[a-z]-[A-Za-z0-9-]{8,}\b|\bAIza[A-Za-z0-9_-]{20,}\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"\b(?:credit card|diagnosis|medical record|patient record|social security)\b)",
    re.IGNORECASE,
)


class PilotError(ValueError):
    """A safe, user-correctable pilot validation error."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def read_json(path: Path, *, limit: int = MAX_FILE_BYTES) -> dict:
    if path.is_symlink() or not path.is_file():
        raise PilotError(f"Input must be a regular file: {path}")
    if path.stat().st_size > limit:
        raise PilotError(f"Input exceeds {limit} bytes: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PilotError(f"Input is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PilotError("JSON root must be an object")
    return value


def clean_text(value: object, field: str, *, minimum: int = 1, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise PilotError(f"{field} must be text")
    if value != value.strip() or not minimum <= len(value) <= maximum:
        raise PilotError(f"{field} must contain {minimum}-{maximum} trimmed characters")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise PilotError(f"{field} contains control characters")
    if SENSITIVE_VALUE.search(value):
        raise PilotError(f"{field} resembles a credential; use synthetic non-secret text")
    return value


def validate_request(request: dict) -> dict:
    if set(request) != REQUEST_KEYS:
        raise PilotError("Request fields must match the documented schema exactly")
    if request["schema_version"] != 1:
        raise PilotError("schema_version must be 1")
    request_id = clean_text(request["request_id"], "request_id", maximum=64)
    if not SIMPLE_ID.fullmatch(request_id):
        raise PilotError("request_id must use lowercase letters, digits, and hyphens")
    workflow = request["workflow"]
    if not isinstance(workflow, str) or workflow not in WORKFLOWS:
        raise PilotError(f"workflow must be one of: {', '.join(sorted(WORKFLOWS))}")
    objective = clean_text(request["objective"], "objective", minimum=12, maximum=500)
    if request["data_classification"] != "synthetic":
        raise PilotError("Only data_classification=synthetic is accepted")
    human_owner = clean_text(request["human_owner"], "human_owner", maximum=64)
    if not PERSON_ID.fullmatch(human_owner):
        raise PilotError("human_owner contains unsupported characters")

    inputs = request["inputs"]
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 8:
        raise PilotError("inputs must contain 1-8 synthetic fields")
    validated_inputs = []
    names = set()
    for index, item in enumerate(inputs):
        if not isinstance(item, dict) or set(item) != INPUT_KEYS:
            raise PilotError(f"inputs[{index}] must contain only name and value")
        name = clean_text(item["name"], f"inputs[{index}].name", maximum=40)
        if not FIELD_NAME.fullmatch(name) or SENSITIVE_NAME.search(name):
            raise PilotError(f"inputs[{index}].name is unsafe or unsupported")
        if name in names:
            raise PilotError(f"duplicate input name: {name}")
        names.add(name)
        validated_inputs.append(
            {"name": name, "value": clean_text(item["value"], f"inputs[{index}].value")}
        )

    allowed_outputs = request["allowed_outputs"]
    if (
        not isinstance(allowed_outputs, list)
        or not 1 <= len(allowed_outputs) <= 4
        or not all(isinstance(output, str) for output in allowed_outputs)
        or len(set(allowed_outputs)) != len(allowed_outputs)
        or any(output not in OUTPUTS for output in allowed_outputs)
    ):
        raise PilotError("allowed_outputs contains duplicates or unsupported values")

    return {
        "schema_version": 1,
        "request_id": request_id,
        "workflow": workflow,
        "objective": objective,
        "data_classification": "synthetic",
        "inputs": validated_inputs,
        "allowed_outputs": sorted(allowed_outputs),
        "human_owner": human_owner,
    }


def expected_steps(workflow: str) -> list[dict]:
    return [
        {
            "step_id": "S1",
            "action": "Validate the supplied synthetic fields",
            "external_effect": False,
        },
        {
            "step_id": "S2",
            "action": WORKFLOWS[workflow],
            "external_effect": False,
        },
        {
            "step_id": "S3",
            "action": "Compare the draft with the allowed outputs and objective",
            "external_effect": False,
        },
        {
            "step_id": "S4",
            "action": "Stop and request an explicit human decision",
            "external_effect": False,
        },
    ]


def validate_plan(plan: dict) -> dict:
    if set(plan) != PLAN_KEYS:
        raise PilotError("Plan fields must match the generated schema exactly")
    if plan["schema_version"] != 1 or plan["status"] != "pending_human_review":
        raise PilotError("Plan version or status is invalid")
    if not isinstance(plan["request_id"], str) or not SIMPLE_ID.fullmatch(plan["request_id"]):
        raise PilotError("Plan request_id is invalid")
    if not isinstance(plan["request_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", plan["request_sha256"]
    ):
        raise PilotError("Plan request hash is invalid")
    if not isinstance(plan["workflow"], str) or plan["workflow"] not in WORKFLOWS:
        raise PilotError("Plan workflow is invalid")
    clean_text(plan["objective"], "plan.objective", minimum=12, maximum=500)
    owner = clean_text(plan["human_owner"], "plan.human_owner", maximum=64)
    if not PERSON_ID.fullmatch(owner):
        raise PilotError("Plan human_owner is invalid")
    outputs = plan["allowed_outputs"]
    if (
        not isinstance(outputs, list)
        or not 1 <= len(outputs) <= 4
        or not all(isinstance(output, str) for output in outputs)
        or outputs != sorted(outputs)
        or len(set(outputs)) != len(outputs)
        or any(output not in OUTPUTS for output in outputs)
    ):
        raise PilotError("Plan allowed_outputs are invalid")
    names = plan["input_names"]
    if (
        not isinstance(names, list)
        or not 1 <= len(names) <= 8
        or not all(isinstance(name, str) for name in names)
        or len(set(names)) != len(names)
    ):
        raise PilotError("Plan input_names are invalid")
    for name in names:
        if not FIELD_NAME.fullmatch(name) or SENSITIVE_NAME.search(name):
            raise PilotError("Plan contains an unsafe input name")
    if plan["steps"] != expected_steps(plan["workflow"]):
        raise PilotError("Plan steps do not match the offline template")
    if plan["capabilities"] != CAPABILITIES:
        raise PilotError("Plan capabilities exceed the offline pilot")
    if plan["decision_required"] != DECISION_NOTICE:
        raise PilotError("Plan decision notice is invalid")
    return plan


def validate_review(review: dict) -> dict:
    if set(review) != REVIEW_KEYS:
        raise PilotError("Review fields must match the generated schema exactly")
    if review["schema_version"] != 1:
        raise PilotError("Review schema_version must be 1")
    if not isinstance(review["request_id"], str) or not SIMPLE_ID.fullmatch(review["request_id"]):
        raise PilotError("Review request_id is invalid")
    if not isinstance(review["plan_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", review["plan_sha256"]
    ):
        raise PilotError("Review plan hash is invalid")
    decision = review["decision"]
    if not isinstance(decision, str):
        raise PilotError("Review decision and status do not match")
    expected = {
        "approve": "approved_for_demo_handoff",
        "reject": "rejected",
    }.get(decision)
    if expected is None or review["status"] != expected:
        raise PilotError("Review decision and status do not match")
    reviewer_label = clean_text(
        review["reviewer_label"], "review.reviewer_label", minimum=2, maximum=64
    )
    if not PERSON_ID.fullmatch(reviewer_label):
        raise PilotError("Review reviewer_label is invalid")
    clean_text(review["reason"], "review.reason", minimum=8, maximum=500)
    if review["live_execution_authorized"] is not False:
        raise PilotError("This pilot cannot authorize live execution")
    return review


def has_symlink_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    return any(candidate.is_symlink() for candidate in (absolute, *absolute.parents))


def workspace(path: Path) -> Path:
    if has_symlink_component(path):
        raise PilotError("Workspace and its ancestors cannot be symlinks")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise PilotError("Workspace must be a directory")
    return path.resolve(strict=True)


def member(root: Path, name: str, *, must_exist: bool) -> Path:
    candidate = Path(name)
    if (
        candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.name in {".", ".."}
        or candidate.name.startswith(".")
        or candidate.suffix != ".json"
    ):
        raise PilotError("Workspace filenames must be one visible .json name")
    target = root / candidate.name
    if target.is_symlink():
        raise PilotError(f"Workspace member cannot be a symlink: {candidate.name}")
    if must_exist and not target.is_file():
        raise PilotError(f"Workspace file does not exist: {candidate.name}")
    return target


def write_new(path: Path, value: dict) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise PilotError(f"Refusing to overwrite: {path.name}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def build_plan(request: dict) -> dict:
    plan = {
        "schema_version": 1,
        "request_id": request["request_id"],
        "request_sha256": digest(request),
        "status": "pending_human_review",
        "workflow": request["workflow"],
        "objective": request["objective"],
        "human_owner": request["human_owner"],
        "allowed_outputs": request["allowed_outputs"],
        "input_names": [item["name"] for item in request["inputs"]],
        "steps": expected_steps(request["workflow"]),
        "capabilities": CAPABILITIES,
        "decision_required": DECISION_NOTICE,
    }
    return validate_plan(plan)


def prepare(request_path: Path, workspace_path: Path, output_name: str) -> dict:
    request = validate_request(read_json(request_path, limit=MAX_REQUEST_BYTES))
    plan = build_plan(request)
    root = workspace(workspace_path)
    write_new(member(root, output_name, must_exist=False), plan)
    return plan


def record_review(
    request_path: Path,
    workspace_path: Path,
    plan_name: str,
    output_name: str,
    decision: str,
    reviewer_label: str,
    reason: str,
) -> dict:
    root = workspace(workspace_path)
    plan = validate_plan(read_json(member(root, plan_name, must_exist=True)))
    request = validate_request(read_json(request_path, limit=MAX_REQUEST_BYTES))
    if plan != build_plan(request):
        raise PilotError("Plan does not match the supplied synthetic request")
    reviewer_label = clean_text(
        reviewer_label, "reviewer_label", minimum=2, maximum=64
    )
    if not PERSON_ID.fullmatch(reviewer_label):
        raise PilotError("reviewer_label contains unsupported characters")
    reason = clean_text(reason, "reason", minimum=8, maximum=500)
    if not isinstance(decision, str) or decision not in {"approve", "reject"}:
        raise PilotError("decision must be approve or reject")
    review = {
        "schema_version": 1,
        "request_id": plan.get("request_id"),
        "plan_sha256": digest(plan),
        "decision": decision,
        "status": "approved_for_demo_handoff" if decision == "approve" else "rejected",
        "reviewer_label": reviewer_label,
        "reason": reason,
        "live_execution_authorized": False,
    }
    write_new(member(root, output_name, must_exist=False), review)
    return review


def verify(
    request_path: Path, workspace_path: Path, plan_name: str, review_name: str
) -> dict:
    root = workspace(workspace_path)
    plan = validate_plan(read_json(member(root, plan_name, must_exist=True)))
    request = validate_request(read_json(request_path, limit=MAX_REQUEST_BYTES))
    if plan != build_plan(request):
        raise PilotError("Plan does not match the supplied synthetic request")
    review = validate_review(read_json(member(root, review_name, must_exist=True)))
    if review.get("plan_sha256") != digest(plan):
        raise PilotError("Review does not match the current plan hash")
    if review.get("request_id") != plan.get("request_id"):
        raise PilotError("Review request_id does not match the plan")
    return review


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    prepare_command = commands.add_parser("prepare")
    prepare_command.add_argument("--request", type=Path, required=True)
    prepare_command.add_argument("--workspace", type=Path, required=True)
    prepare_command.add_argument("--output", default="plan.json")

    review_command = commands.add_parser("review")
    review_command.add_argument("--request", type=Path, required=True)
    review_command.add_argument("--workspace", type=Path, required=True)
    review_command.add_argument("--plan", default="plan.json")
    review_command.add_argument("--output", default="review.json")
    review_command.add_argument("--decision", choices=("approve", "reject"), required=True)
    review_command.add_argument("--reviewer-label", required=True)
    review_command.add_argument("--reason", required=True)

    verify_command = commands.add_parser("verify")
    verify_command.add_argument("--request", type=Path, required=True)
    verify_command.add_argument("--workspace", type=Path, required=True)
    verify_command.add_argument("--plan", default="plan.json")
    verify_command.add_argument("--review", default="review.json")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.request, args.workspace, args.output)
            print(f"Prepared {result['request_id']}; status=pending_human_review")
        elif args.command == "review":
            result = record_review(
                args.request,
                args.workspace,
                args.plan,
                args.output,
                args.decision,
                args.reviewer_label,
                args.reason,
            )
            print(f"Recorded {result['decision']}; status={result['status']}")
        else:
            result = verify(args.request, args.workspace, args.plan, args.review)
            print(f"Verified {result['request_id']}; status={result['status']}")
    except PilotError as exc:
        print(f"Pilot error: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
