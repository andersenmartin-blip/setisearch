#!/usr/bin/env python3
"""Write a non-numerical closure of the unrecovered 14 October study.

This script only reads published input definitions and the local recovery audit.
It never imports, executes, or retries a scientific worker or RNG.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
RECOVERED = ROOT / "recovered_sixscan_burst_20261014"
STUDY = "SETI_SIXSCAN_BURST_20261014"
UNKNOWN = "UNKNOWN_UNRECOVERED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    cases = json.loads((RECOVERED / "case_bank.json").read_text())
    exposed = json.loads((RECOVERED / "real_baselines.json").read_text())
    scope = json.loads((RECOVERED / "SCOPE.json").read_text())
    remote = json.loads((OUT / "REMOTE_RECOVERY_READBACK.json").read_text())
    assert len(cases) == 205 and len(exposed) == 9
    assert len({c["case_id"] for c in cases}) == 205
    assert all(c["case_id"].startswith(STUDY + ":") for c in cases + exposed)
    pin_results = []
    for pin in scope["code_pins"]:
        p = RECOVERED / pin["path"]
        actual = sha256(p)
        assert actual == pin["sha256"] and p.stat().st_size == pin["bytes"], pin["path"]
        pin_results.append({**pin, "verification": "MATCH"})
    assert len(pin_results) == 17
    assert sha256(RECOVERED / "SCOPE.json") == "8bb84b8cd8f0a6756523139bff8b8869e1a4ad478a07d84004d1c199cf53e077"
    public_file_checks = []
    assert len(remote["stage_files"]) == 20
    for entry in remote["stage_files"]:
        data = (RECOVERED / entry["path"]).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert blob == entry["sha"] and len(data) == entry["size"], entry["path"]
        public_file_checks.append({"path": entry["path"], "bytes": len(data), "Git_blob_sha": blob, "sha256": hashlib.sha256(data).hexdigest(), "verification": "MATCH"})
    fields = ["index", "case_id", "family", "serial", "seed_sha256", "primary_endpoint", "qa_endpoint", "measured_score", "measured_recovery", "measured_veto", "measured_rank", "reuse_policy", "reason"]
    with (OUT / "CASE_STATUS.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, c in enumerate(cases):
            w.writerow({
                "index": i, "case_id": c["case_id"], "family": c["family"],
                "serial": c["serial"], "seed_sha256": c["seed_sha256"],
                "primary_endpoint": UNKNOWN, "qa_endpoint": UNKNOWN,
                "reuse_policy": "RETIRED_DO_NOT_RERUN",
                "reason": "No authoritative numerical output, claim, whole-child resource receipt or final phase closure recovered; absence does not establish NOT_RUN or a measured null.",
            })
    with (OUT / "EXPOSED_STATUS.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["index", "case_id", "family", "native_chunk_index", "core_q", "primary_endpoint", "qa_endpoint", "measured_candidate_count", "reuse_policy", "reason"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, c in enumerate(exposed):
            w.writerow({
                "index": i, "case_id": c["case_id"], "family": c["family"],
                "native_chunk_index": c["native_chunk_index"], "core_q": c["core_q"],
                "primary_endpoint": UNKNOWN, "qa_endpoint": UNKNOWN,
                "reuse_policy": "RETIRED_DO_NOT_RERUN",
                "reason": "Final execution and admission endpoints unrecovered; no claim about whether the exposed diagnostic ran.",
            })
    created = datetime.now(timezone.utc).isoformat()
    closure = {
        "schema": "SETI_UNRECOVERED_STUDY_CLOSURE_V1",
        "created_utc": created,
        "study_id": STUDY,
        "status": "CLOSED_UNKNOWN_UNRECOVERED_RETIRED",
        "reason": "Restored runtime retained partial inputs but no authoritative numerical output, claim, phase closure, child resource receipt or independent numerical QA endpoint for this study.",
        "scientific_endpoint": UNKNOWN,
        "scientific_integrity_gate": "NOT_ESTABLISHED",
        "scientific_joint_gate": "NOT_ESTABLISHED",
        "unknown_is_not_null": True,
        "unknown_is_not_NOT_RUN": True,
        "no_measured_outcome_rates_reported": True,
        "retirement": {
            "synthetic_case_count": 205,
            "exposed_case_count": 9,
            "all_primary_and_QA_final_endpoints": UNKNOWN,
            "all_old_identities_retired": True,
            "retry_redraw_relabel_or_silent_replacement_authorized": False,
        },
        "case_family_counts": dict(collections.Counter(c["family"] for c in cases)),
        "published_freeze": {
            "repository": "andersenmartin-blip/setisearch",
            "branch": "m43-support-qualification",
            "preregistration_commit": "bc3a42f7d99dfa19af3070b11e8eb7cafa11984f",
            "GO_commit": "101138540dee6c01b40703b6789c5b3c283c613d",
            "scope_sha256": sha256(RECOVERED / "SCOPE.json"),
            "restored_public_files": 20,
            "all_scope_code_pins_exact": True,
            "scope_code_pin_count": 17,
            "code_pin_checks": pin_results,
            "all_20_public_Git_blobs_exact": True,
            "public_file_checks": public_file_checks,
        },
        "recovery_evidence": {
            "local_audit_path": "LOCAL_RECOVERY_AUDIT.json",
            "local_audit_sha256": sha256(OUT / "LOCAL_RECOVERY_AUDIT.json"),
            "remote_readback_path": "REMOTE_RECOVERY_READBACK.json",
            "remote_readback_sha256": sha256(OUT / "REMOTE_RECOVERY_READBACK.json"),
            "root_reported_remote_checks": {
                "provenance": "Root agent recovery inspection documented in REMOTE_RECOVERY_READBACK.json. This closure generator independently checks all 20 recovered public Git blob hashes and 17 scope SHA256 pins, but does not call remote services.",
                "GitHub_research_branch_endpoint": "GO commit 101138540dee6c01b40703b6789c5b3c283c613d; no later numerical publication recovered.",
                "Library_exact_title_search": "No matching new six-scan result archive recovered by exact-title search; this is a bounded search, not proof that no file exists anywhere.",
            },
            "prior_conversation_progress_only": {
                "approximate_last_observed_utc": "2026-10-14T18:43:00+00:00",
                "calibration_exit_zero_reported": 16,
                "calibration_live_reported": 4,
                "calibration_unsubmitted_at_snapshot_reported": 43,
                "reported_whole_child_CPU_s_rounded": 2592.180,
                "not_final_closure": True,
                "not_recovered_numerical_evidence": True,
                "no_inference_about_later_execution": True,
            },
        },
        "resource_accounting": {
            "old_stage_envelope_CPU_s": 90000,
            "historical_unreconciled_debit_CPU_s": 90000,
            "debit_basis": "Conservative accounting reservation of the entire old envelope; not an assertion of measured CPU consumption.",
            "measured_final_whole_child_CPU_s": None,
            "metadata_delivery_reservation_CPU_s_included_in_envelope": 1000,
            "old_envelope_capacity_released_CPU_s": 0,
            "historical_reset_refund_or_double_allocation": False,
            "new_science_jobs_run_by_this_closure": 0,
            "cost_DKK": 0,
            "new_telescope_requests": 0,
            "new_telescope_payload_bytes": 0,
        },
        "continuation_policy": {
            "fresh_study": "SETI_SIXSCAN_BURST_20261015_RECOVERY_V1",
            "fresh_study_status_at_this_closure": "SEPARATE_PREPARATION_NO_RESULTS_ASSERTED",
            "fresh_identities_seeds_and_preregistration_required": True,
            "same_declared_geometry_and_scientific_rules": True,
            "no_old_outcome_based_scientific_tuning": True,
            "engineering_parallel_workers_old": 4,
            "engineering_parallel_workers_fresh": 8,
            "fresh_separate_aggregate_CPU_s_cap": 90000,
            "new_separate_bounded_resource_allocation_required": True,
            "old_and_fresh_results_must_not_be_pooled": True,
        },
        "preserved": {
            "qualified_SETI_detection": False,
            "original_A_B": "FAIL_CLOSED",
            "protected_2016_closed": True,
            "unavailable_2019_closed": True,
            "formal_checkpoint": "2026-10-20",
            "exposed_bands_are_postselected_2017_data": True,
            "Gamma16_model_ranks_are_not_sky_FAP": True,
        },
        "mutations": "Closure documents and delivery packaging only outside original frozen stages. Original partial stage and exact restored public sources are not edited.",
    }
    write_json(OUT / "CLOSURE.json", closure)
    md = """# SETI: afslutning af den ikke genfundne seks-scan-kørsel

Den 14. oktober-kørsel lukkes med **`UNKNOWN_UNRECOVERED`**. De oprindelige
205 syntetiske identiteter og ni allerede eksponerede bånddiagnostikker pensioneres
og køres ikke igen. Der foreligger ingen genfundne måleresultater, som kan bruges
til at godkende metoden eller beregne en succesrate.

Efter gendannelse af arbejdsmiljøet manglede de numeriske output, claim-filer,
faseafslutninger, børneprocessernes ressourcebilag og den uafhængige numeriske QA.
En lokal gennemgang er bevaret i `LOCAL_RECOVERY_AUDIT.json`. Root-agentens
fjernkontrol fandt forskningsgrenen ved det publicerede GO og fandt ikke et nyt
resultatarkiv ved en præcis titelsøgning. Disse afgrænsede søgninger beviser ikke,
at ingen ukendt kopi kan eksistere andre steder.

Kildekoden kan derimod genfindes: de 20 publicerede filer er gendannet separat fra
det ufuldstændige lokale stadium. Alle 17 SHA-256-pins i den publicerede `SCOPE.json`
stemmer byte for byte. Det dokumenterer den fastlåste metode, ikke dens udfald.

| Registrering | Status |
|---|---|
| Præregistrering | `bc3a42f7d99dfa19af3070b11e8eb7cafa11984f` |
| GO | `101138540dee6c01b40703b6789c5b3c283c613d` |
| SCOPE SHA-256 | `8bb84b8cd8f0a6756523139bff8b8869e1a4ad478a07d84004d1c199cf53e077` |
| Syntetiske slutpunkter | 205 primær- og 205 QA-slutpunkter `UNKNOWN_UNRECOVERED` |
| Eksponerede slutpunkter | 9 primær- og 9 QA-slutpunkter `UNKNOWN_UNRECOVERED` |
| Metodens integritets- og fælles resultatkrav | Ikke etableret |

Den seneste rapporterede fremdrift i samtalen var cirka 14. oktober kl. 18:43 UTC:
16 støjreferencer var meldt afsluttet med exitkode 0, fire var i gang, og 43 var
endnu ikke indsendt i dette øjeblik. Den afrundede rapporterede CPU-tid var
2.592,180 sekunder. Dette er et tidligere øjebliksbillede. Det fortæller ikke,
hvor langt processen eller den ventende hjælper senere nåede, og er ikke en
genfundet slutafslutning eller et numerisk kontrolresultat.

`CASE_STATUS.csv` indeholder alle 205 syntetiske identiteter og deres oprindelige
seed-hash. `EXPOSED_STATUS.csv` indeholder de ni historiske bånd. Alle målte felter
står tomme. Manglende dokumentation tælles hverken som en målt nulobservation,
en fejlmåling eller `NOT_RUN`.

| Syntetisk familie | Fastlagt antal | Genfundet slutresultat |
|---|---:|---|
| Støjkalibrering | 63 | Ukendt |
| Stærke signaler | 14 | Ukendt |
| Driftspunkter | 48 | Ukendt |
| Matchet interferens | 24 | Ukendt |
| Uafhængige nulforløb | 32 | Ukendt |
| Enkelt-række-transienter | 12 | Ukendt |
| Nærliggende OFF-forurening | 12 | Ukendt |

Hele det gamle loft på **90.000 CPU-sekunder** bevares som en konservativ,
uafstemt historisk debitering. Det er en regnskabsmæssig reservation; det er ikke
en påstand om 90.000 målte CPU-sekunder. De 1.000 sekunder til metadata og levering
er allerede indeholdt i beløbet. Ingen gammel kapacitet frigives, refunderes
eller tildeles igen. Den tidligere rapports afrundede delsum kan ikke bruges
til at beregne en restkapacitet.

Fortsættelsen forberedes som en særskilt bank, `SETI_SIXSCAN_BURST_20261015_RECOVERY_V1`, med
samme erklærede geometri og videnskabelige regler, nye identiteter og seeds,
ny præregistrering og en særskilt begrænset ressourcetildeling. Denne afslutning
indeholder ingen resultater fra den nye bank. Den nye bank er ikke en gentagelse
af gamle identiteter, og dens resultater må ikke lægges sammen med ukendte gamle
resultater. Der er ikke ændret på de videnskabelige regler ud fra gamle udfald.
Den tekniske parallelitet hæves fra fire til otte samtidige arbejdere; det nye,
særskilte samlede loft er fortsat 90.000 CPU-sekunder.

Der er fortsat **ingen kvalificeret SETI-detektion**. Den oprindelige A/B-status
er `FAIL_CLOSED`. De beskyttede 2016-data og den utilgængelige 2019-rute forbliver
lukkede. Det formelle kontrolpunkt er 20. oktober 2026. De ni gamle bånd kommer
fra et allerede eksponeret og efterudvalgt besøg i 2017; eventuelle Gamma16-rangtal
er en modeldiagnostik og kan ikke fortolkes som himlens falsk-alarm-sandsynlighed.
Der er ingen nye teleskopforespørgsler eller teleskopbytes og ingen udgift i DKK.

Reproduktionspakken indeholder de præcise publicerede input, audit og afslutning,
status for alle identiteter samt det uændrede oprindelige kildearkiv
`SETI_NATIVE_SPOR_2026-10-14.zip`. Pakningen kontrollerer ZIP-CRC og SHA-256 for
hver leveret fil, alle 17 kildepins og det indlejrede kildearkiv. Den indeholder
ingen genskabte eller opdigtede numeriske resultater.
"""
    (OUT / "CLOSURE.md").write_text(md, encoding="utf-8")
    print(json.dumps({"status": "CLOSURE_WRITTEN", "synthetic_rows": 205, "exposed_rows": 9, "pins_verified": 17}))


if __name__ == "__main__":
    main()
