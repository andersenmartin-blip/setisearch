#!/usr/bin/env python3
"""Conditional sample-size arithmetic only; no experiment or detector imports."""
from decimal import Decimal, localcontext
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
D = Decimal


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def text_decimal(value):
    return format(value, "f")


def minimal_count(alpha, adverse_limit):
    # No float logarithm: test integer powers and retain both boundary witnesses.
    complement = D(1) - adverse_limit
    n = 1
    while complement ** n > alpha:
        n += 1
    before = complement ** (n - 1)
    at = complement ** n
    assert before > alpha and at <= alpha
    return {
        "alpha": text_decimal(alpha),
        "adverse_probability_limit": text_decimal(adverse_limit),
        "success_probability_target": text_decimal(complement),
        "minimal_cadences_per_class": n,
        "probability_of_zero_events_at_target_n_minus_1": text_decimal(before),
        "probability_of_zero_events_at_target_n": text_decimal(at),
        "minimality_passed": True,
    }


with localcontext() as ctx:
    ctx.prec = 90
    historical_b_cpu = D("11676.036546")
    historical_method_cpu = D("5407.226987")
    historical_b_count = 142
    historical_method_count = 64
    b_mean = historical_b_cpu / D(historical_b_count)
    method_mean = historical_method_cpu / D(historical_method_count)
    unit_cost = max(b_mean, method_mean)
    assert unit_cost == D("84.487921671875")
    stress = D(2)
    remaining_before_design = D("6312.705144981004")
    design_reservation = D(100)
    after_design = remaining_before_design - design_reservation
    future_reservation = D(2000)
    arithmetic_available = after_design - future_reservation
    assert after_design == D("6212.705144981004")
    assert arithmetic_available == D("4212.705144981004")

    rows = []
    for mode, classes, alpha in (
        ("single_class_95_percent", 1, D("0.05")),
        ("four_class_bonferroni_simultaneous_95_percent", 4, D("0.0125")),
    ):
        for target in (D("0.10"), D("0.05"), D("0.01")):
            row = minimal_count(alpha, target)
            n = row["minimal_cadences_per_class"]
            row.update({
                "confidence_mode": mode,
                "number_of_classes": classes,
                "total_cadences_for_all_classes": n * classes,
                "per_class_retrospective_cost_cpu_s": text_decimal(D(n) * unit_cost),
                "per_class_twice_average_stress_cpu_s": text_decimal(D(n) * unit_cost * stress),
                "all_classes_retrospective_cost_cpu_s": text_decimal(D(n * classes) * unit_cost),
                "all_classes_twice_average_stress_cpu_s": text_decimal(D(n * classes) * unit_cost * stress),
                "arithmetic_budget_comparison_average": D(n * classes) * unit_cost <= arithmetic_available,
                "arithmetic_budget_comparison_twice_average": D(n * classes) * unit_cost * stress <= arithmetic_available,
                "tests_admitted": False,
            })
            rows.append(row)

    all_success = []
    for row in rows:
        if D(row["adverse_probability_limit"]) in (D("0.10"), D("0.05")):
            all_success.append({
                "confidence_mode": row["confidence_mode"],
                "success_probability_target": row["success_probability_target"],
                "minimal_all_success_cadences_per_class": row["minimal_cadences_per_class"],
                "alpha": row["alpha"],
                "same_boundary_power_witnesses_as_zero_adverse_row": True,
                "condition": "Every one of the n independent identical-probability cadences succeeds.",
            })

    evidence = {
        "review_status": "PASS_INDEPENDENT_DECIMAL_SAMPLE_SIZE_MINIMALITY",
        "precision_decimal_digits": ctx.prec,
        "method": "Integer n search and Decimal powers at n and n-1; no floating logarithm used.",
        "scope": {
            "new_scientific_draws": 0,
            "new_detector_scores": 0,
            "generator_or_detector_imports": 0,
            "archives_maps_raw_payloads_old_holdouts_opened": 0,
            "qualification_panel_or_seed_identities_created": False,
        },
        "conditional_assumptions": [
            "Within each class, n cadences are independent Bernoulli trials with one unchanged event probability p.",
            "Class definitions and the binary event are fixed before observing the trials.",
            "All n observations contain zero adverse events, or all n are successes for the dual lower bound.",
            "Bonferroni uses four per-class one-sided intervals at alpha=0.05/4; cross-class independence is unnecessary for the union bound.",
            "Existing heterogeneous diagnostic cases, synthetic noise laws and correlated carrier responses do not establish these assumptions for real sky data.",
        ],
        "conditional_formulae": {
            "zero_event_probability": "P(K=0 | p,n) = (1-p)^n",
            "zero_event_upper_limit": "p_U = 1 - alpha^(1/n)",
            "minimum_n_for_upper_target": "smallest integer n with (1-p_target)^n <= alpha",
            "all_success_lower_limit": "p_L = alpha^(1/n)",
            "minimum_n_for_success_lower_target": "smallest integer n with p_success_target^n <= alpha",
        },
        "zero_adverse_event_rows": rows,
        "all_success_rows": all_success,
        "retrospective_cost_illustration": {
            "historical_B142_total_fully_metred_cpu_s": text_decimal(historical_b_cpu),
            "historical_B142_mean_cpu_s": text_decimal(b_mean),
            "historical_METHOD64_total_fully_metred_cpu_s": text_decimal(historical_method_cpu),
            "historical_METHOD64_mean_cpu_s": text_decimal(method_mean),
            "illustrative_cpu_s_per_cadence_maximum_of_means": text_decimal(unit_cost),
            "stress_multiplier": text_decimal(stress),
            "caveat": "Historical averages are not execution caps, forecasts, allocation, or proof of fit. Changed-method controls, figures, independent audits, storage, initialization and publication overhead are excluded.",
        },
        "budget_arithmetic": {
            "remaining_before_design_cpu_s": text_decimal(remaining_before_design),
            "root_design_reservation_debited_once_cpu_s": text_decimal(design_reservation),
            "remaining_after_design_cpu_s": text_decimal(after_design),
            "minimum_future_report_reproduction_reservation_cpu_s": text_decimal(future_reservation),
            "arithmetic_difference_cpu_s": text_decimal(arithmetic_available),
            "floor_cadence_count_at_historical_maximum_mean": int(arithmetic_available // unit_cost),
            "floor_cadence_count_at_twice_historical_maximum_mean": int(arithmetic_available // (stress * unit_cost)),
            "new_tests_admitted": False,
            "component_job_metering_is_not_an_additional_debit": True,
        },
        "interpretation": "Even one class at the 1% upper target requires 299 ideal independent all-clear cadences. Four-class simultaneous 1% requires 437 per class, 1748 total. Neither approaches the arithmetic budget. Controlled descriptive work and explicit future acceptance criteria are appropriate; this calculation does not calibrate an empirical sky false-alarm probability or validate the detector.",
    }
    dump(OUT / "NUMERIC_DESIGN_REVIEW.json", evidence)

    report = [
        "# Betingede stikprøvekrav til en senere SETI-plan",
        "",
        "Kontrolleret 8. oktober 2026. Dette er aritmetik til planlægning; ingen nye forsøg er startet, og ingen kvalifikationspaneler eller seeds er oprettet.",
        "",
        "Ved **nul uønskede hændelser** er den eksakte ensidige øvre grænse $p_U=1-\\alpha^{1/n}$. Minimum er det første heltal $n$, hvor $(1-p_\\mathrm{mål})^n\\leq\\alpha$. Beregningen søger over heltal og kontrollerer begge naboværdier med 90-cifret Decimal-aritmetik. Ingen flydende logaritme er brugt.",
        "",
        "| Ønsket øvre grænse | Én klasse, 95 % | Fire klasser, samlet mindst 95 %, pr. klasse | Fire klasser, samlet antal |",
        "|---|---:|---:|---:|",
    ]
    for target in (D("0.10"), D("0.05"), D("0.01")):
        one = next(r for r in rows if r["number_of_classes"] == 1 and D(r["adverse_probability_limit"]) == target)
        four = next(r for r in rows if r["number_of_classes"] == 4 and D(r["adverse_probability_limit"]) == target)
        report.append(f"| {int(target * 100)} % | {one['minimal_cadences_per_class']} | {four['minimal_cadences_per_class']} | {four['total_cadences_for_all_classes']} |")
    report += [
        "",
        "Fireklassetilfældet bruger Bonferroni med $\\alpha=0,05/4=0,0125$ pr. klasse. Det kræver ikke indbyrdes uafhængighed mellem klasserne, men hver enkelt klasses interval skal være gyldigt. Minimumsbeviserne $n-1$ og $n$ er gemt fuldt i JSON-filen.",
        "",
        "Ved **udelukkende succeser** er den ensidige nedre grænse $p_L=\\alpha^{1/n}$. En nedre grænse på 90 % kræver 29 succeser i én klasse eller 42 pr. klasse ved fire samtidige klassekrav; 95 % kræver henholdsvis 59 og 86. Det er det samme minimumsbevis med hændelsen omvendt.",
        "",
        "**Forudsætningerne er hypotetiske:** Uafhængige kadencer, ens og uændret hændelsessandsynlighed inden for hver klasse samt klassifikation og succeskriterium fastlagt før observationerne. De tidligere heterogene celler med én realisering og tusindvis af korrelerede carriers kan ikke tælles som sådanne forsøg. Støjkontroller med syntetiske love fastlægger heller ikke falskalarmraten på teleskopdata.",
        "",
        "Gennemsnittene for de afsluttede panelers målte jobs, inklusive børn og koordinering, er B142: **82,225609478873… CPU-s pr. kadence** og METHOD64: **84,487921671875 CPU-s**. De betyder ikke, at al historisk forberedelse, arkivering, review eller offentliggørelse er fuldt målt. Grundlaget fremgår af [HISTORICAL_COST_INPUTS.json](HISTORICAL_COST_INPUTS.json). Tabellen bruger det største jobgennemsnit; en ekstra kolonne viser blot to gange dette gennemsnit.",
        "",
        "| Krav | Kadencer i alt | Historisk gennemsnit, CPU-s | To gange gennemsnittet, CPU-s |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        name = ("Én klasse" if r["number_of_classes"] == 1 else "Fire samtidige klasser") + f", ≤{int(D(r['adverse_probability_limit']) * 100)} %"
        report.append(f"| {name} | {r['total_cadences_for_all_classes']} | {D(r['all_classes_retrospective_cost_cpu_s']):.3f} | {D(r['all_classes_twice_average_stress_cpu_s']):.3f} |".replace(".", ","))
    report += [
        "",
        "Tallene er **hverken kørselstidslofter, prognoser eller adgang til at starte tests**. En ændret metode, dens kontrolforsøg, figurer, uafhængige audits, lagring, initialisering og offentliggørelse er ikke medregnet. Historiske gennemsnit beviser derfor ikke, at en ny udførelse kan rummes.",
        "",
        "Efter den nye designreservation på 100 CPU-s er restsaldoen **6.212,705144981004 CPU-s**. Med mindst 2.000 CPU-s afsat til senere reproduktion og slutrapport er den aritmetiske forskel **4.212,705144981004 CPU-s**. Det svarer højst til 49 historiske gennemsnitskadencer eller 24 ved dobbeltgennemsnittet, før øvrige udgifter; det er ingen testbevilling. Denne komponents faktisk målte CPU er indeholdt i reservationen og trækkes ikke fra igen.",
        "",
        "Allerede én klasses 5 %-krav overstiger den aritmetiske forskel ved det historiske gennemsnit; 10 %-kravet overstiger den ved dobbeltgennemsnittet. Et 1 %-krav kræver mindst 299 ideelt uafhængige kadencer i én klasse eller 1.748 i fire samtidige klasser. Den konkrete næste plan bør derfor formulere afgrænsede, beskrivende kontroller og dokumentere metodefejl, frem for at love procentniveau for falskalarmraten på himlen. Den nuværende metode er fortsat ikke kvalificeret.",
        "",
    ]
    (OUT / "NUMERIC_DESIGN_REVIEW.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"review_status": evidence["review_status"], "minimum_counts": [r["minimal_cadences_per_class"] for r in rows], "remaining_after_design_cpu_s": text_decimal(after_design), "arithmetic_difference_cpu_s": text_decimal(arithmetic_available)}, ensure_ascii=False))
