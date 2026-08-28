"""Adversarial lifecycle tests for the M37 v0.6 run journal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from seti_repeater import run_state_v0p6 as state
from seti_repeater.search_v0p6 import (
    V0P6ContractError,
    V0P6IncompleteError,
    canonical_json_bytes,
)


def _digest(index: int) -> str:
    return hashlib.sha256(f"artifact-{index}".encode()).hexdigest()


def _metadata(stage: str) -> dict[str, object]:
    if stage in {"initialized", "factor_bundle_ready"}:
        return {
            "spectral_access_authorized": False,
            "spectral_dataset_values_read": False,
            "test_stage": stage,
        }
    if stage == "spectral_access_authorized":
        return {
            "spectral_access_authorized": True,
            "spectral_dataset_values_read": False,
            "authorization_scope": state.M37_SPECTRAL_AUTHORIZATION_SCOPE,
            "authorization_receipt_sha256": _digest(99),
            "test_stage": stage,
        }
    return {
        "spectral_access_authorized": True,
        "spectral_dataset_values_read": True,
        "test_stage": stage,
    }


class M37RunJournalTests(unittest.TestCase):
    def _create(self, directory: str):
        path = Path(directory) / "m37-run.journal"
        receipt = state.create_m37_run_journal(
            path,
            run_id="m37-synthetic-run-001",
            initialization_sha256=_digest(0),
            metadata=_metadata("initialized"),
        )
        return path, receipt

    def test_full_exact_stage_order_reaches_published(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._create(directory)
            for index, stage_name in enumerate(state.M37_RUN_STAGES[1:], start=1):
                receipt = state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=receipt.head_sha256,
                    stage=stage_name,
                    artifact_sha256=_digest(index),
                    metadata=_metadata(stage_name),
                )
            self.assertTrue(receipt.complete)
            self.assertFalse(receipt.invalid)
            self.assertEqual(receipt.stage, "published")
            self.assertEqual(receipt.event_count, len(state.M37_RUN_STAGES))
            self.assertEqual(
                state.read_m37_run_journal(
                    path, expected_head_sha256=receipt.head_sha256
                ),
                receipt,
            )
            with self.assertRaisesRegex(V0P6IncompleteError, "terminal"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=receipt.head_sha256,
                    stage="published",
                    artifact_sha256=_digest(100),
                    metadata=_metadata("published"),
                )

    def test_skip_repeat_and_stale_restart_receipt_do_not_append(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, initial = self._create(directory)
            initial_bytes = path.read_bytes()
            with self.assertRaisesRegex(V0P6IncompleteError, "skip"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=initial.head_sha256,
                    stage="extraction_complete",
                    artifact_sha256=_digest(2),
                    metadata=_metadata("extraction_complete"),
                )
            self.assertEqual(path.read_bytes(), initial_bytes)
            factor = state.advance_m37_run_journal(
                path,
                expected_head_sha256=initial.head_sha256,
                stage="factor_bundle_ready",
                artifact_sha256=_digest(1),
                metadata=_metadata("factor_bundle_ready"),
            )
            with self.assertRaisesRegex(V0P6IncompleteError, "changed since"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=initial.head_sha256,
                    stage="spectral_access_authorized",
                    artifact_sha256=_digest(2),
                    metadata=_metadata("spectral_access_authorized"),
                )
            self.assertEqual(
                state.read_m37_run_journal(path).head_sha256,
                factor.head_sha256,
            )

    def test_authorization_scope_and_receipt_are_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._create(directory)
            receipt = state.advance_m37_run_journal(
                path,
                expected_head_sha256=receipt.head_sha256,
                stage="factor_bundle_ready",
                artifact_sha256=_digest(1),
                metadata=_metadata("factor_bundle_ready"),
            )
            before = path.read_bytes()
            bad = _metadata("spectral_access_authorized")
            bad["authorization_scope"] = "broader-than-frozen"
            with self.assertRaisesRegex(V0P6IncompleteError, "frozen scope"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=receipt.head_sha256,
                    stage="spectral_access_authorized",
                    artifact_sha256=_digest(2),
                    metadata=bad,
                )
            self.assertEqual(path.read_bytes(), before)
            bad = _metadata("spectral_access_authorized")
            bad["authorization_receipt_sha256"] = 123
            with self.assertRaisesRegex(V0P6ContractError, "authorization receipt"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=receipt.head_sha256,
                    stage="spectral_access_authorized",
                    artifact_sha256=_digest(2),
                    metadata=bad,
                )
            self.assertEqual(path.read_bytes(), before)

    def test_invalidation_is_permanent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._create(directory)
            invalid = state.invalidate_m37_run_journal(
                path,
                expected_head_sha256=receipt.head_sha256,
                evidence_sha256=_digest(50),
                reason_code="synthetic-cap-breach",
                metadata={"measured_bytes": 999},
            )
            self.assertTrue(invalid.invalid)
            self.assertFalse(invalid.complete)
            self.assertEqual(invalid.stage, state.M37_INVALID_STAGE)
            with self.assertRaisesRegex(V0P6IncompleteError, "terminal"):
                state.advance_m37_run_journal(
                    path,
                    expected_head_sha256=invalid.head_sha256,
                    stage="factor_bundle_ready",
                    artifact_sha256=_digest(1),
                    metadata=_metadata("factor_bundle_ready"),
                )

    def test_resealed_earlier_event_breaks_the_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, initial = self._create(directory)
            state.advance_m37_run_journal(
                path,
                expected_head_sha256=initial.head_sha256,
                stage="factor_bundle_ready",
                artifact_sha256=_digest(1),
                metadata=_metadata("factor_bundle_ready"),
            )
            events = [json.loads(line) for line in path.read_bytes().splitlines()]
            first = dict(events[0])
            first["artifact_sha256"] = _digest(77)
            first.pop("event_sha256")
            first["event_sha256"] = hashlib.sha256(
                canonical_json_bytes(first)
            ).hexdigest()
            path.write_bytes(
                canonical_json_bytes(first) + canonical_json_bytes(events[1])
            )
            with self.assertRaisesRegex(V0P6IncompleteError, "hash chain"):
                state.read_m37_run_journal(path)

    def test_creation_never_overwrites_and_truncation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._create(directory)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                state.create_m37_run_journal(
                    path,
                    run_id="another-run",
                    initialization_sha256=_digest(0),
                    metadata=_metadata("initialized"),
                )
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(V0P6IncompleteError, "supplied head"):
                state.read_m37_run_journal(
                    path, expected_head_sha256="f" * 64
                )
            path.write_bytes(original[:-1])
            with self.assertRaisesRegex(V0P6IncompleteError, "final newline"):
                state.read_m37_run_journal(path)


if __name__ == "__main__":
    unittest.main()
