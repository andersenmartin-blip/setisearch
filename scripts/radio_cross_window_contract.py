"""Build and adversarially exercise the identity-only cross-window contract."""
import copy
import hashlib
import json
from pathlib import Path

from seti_repeater import calibration_transfer_radio as transfer

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "results_radio_motion_2026-09-26/prospective_design.json"
OUT = ROOT / "results_radio_cross_window_2026-09-26"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True,
                                       allow_nan=False) + "\n")


def rejected(fn):
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    raise RuntimeError("negative control unexpectedly accepted")


def main():
    OUT.mkdir(exist_ok=True)
    design = json.loads(DESIGN.read_text())
    contract = transfer.build_contract(design)
    windows = {item.role: item for item in contract.windows}
    source_context = hashlib.sha256(b"prospective-calibration-context").hexdigest()
    destination_context = hashlib.sha256(b"prospective-validation-context").hexdigest()
    certificate = transfer.ExactContextCertificate(
        windows["calibration"].identity, source_context,
        hashlib.sha256(b"prospective-receipt-placeholder-no-values").hexdigest(),
        "synthetic")
    request = transfer.prepare_transfer_request(
        contract, certificate, source_role="calibration", destination_role="validation",
        source_context_sha256=source_context,
        destination_context_sha256=destination_context)
    tampered = copy.deepcopy(design)
    tampered["windows"][1]["payload_keys"][0][
        "chunk_coordinates_time_feed_frequency"][0][2] = 150
    rejections = {
        "certificate_reused_for_validation_context": rejected(lambda:
            certificate.validate_for_exact_context(
                windows["validation"].identity, destination_context)),
        "same_context_transfer": rejected(lambda: transfer.prepare_transfer_request(
            contract, certificate, source_role="calibration", destination_role="validation",
            source_context_sha256=source_context,
            destination_context_sha256=source_context)),
        "calibration_to_pilot_shortcut": rejected(lambda:
            transfer.prepare_transfer_request(
                contract, certificate, source_role="calibration", destination_role="pilot",
                source_context_sha256=source_context,
                destination_context_sha256=destination_context)),
        "payload_coordinate_tamper": rejected(lambda: transfer.build_contract(tampered)),
    }
    write("contract.json", {**contract.record(), "contract_sha256": contract.identity,
        "window_records": {item.role: item.record() for item in contract.windows}})
    write("prepared_request.json", request)
    write("rejection_evidence.json", rejections)
    result = {
        "schema": "radio-cross-window-contract-result-v1",
        "status": "IDENTITY_CONTRACT_PASS_TRANSFER_NOT_QUALIFIED",
        "contract_sha256": contract.identity,
        "window_identities": {item.role: item.identity for item in contract.windows},
        "window_payload_hashes": {item.role: item.payload_keys_sha256
                                  for item in contract.windows},
        "decoded_payload_identity_count": 18,
        "normalization_block_identity_count": 12,
        "negative_controls_rejected": len(rejections),
        "prepared_request_sha256": request["request_sha256"],
        "prepared_request_blocker_count": len(request["blockers"]),
        "threshold_transfer_authorized": False,
        "source_pointing_resolved": False,
        "physical_model_qualified": False,
        "scientific_candidate_selection_authorized": False,
        "telescope_values_opened": False,
        "telescope_requests": 0,
    }
    write("result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
