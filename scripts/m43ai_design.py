"""Metadata-only M43AI prospective panel; no native scores or model selection."""
import copy
import hashlib
import json


def translated_case(original, index):
    """Preserve the full 14-case factorial structure at a new carrier/strength."""
    case = copy.deepcopy(original)
    def transform(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == 'score_index':
                    value[k] = v + 211
                elif k == 'strength':
                    value[k] = v * (15/16)
                else:
                    transform(v)
        elif isinstance(value, list):
            for v in value:
                transform(v)
    transform(case)
    case.update(name=f'ai_validation{index:03d}', panel='ai_validation', case_index=index,
                source_name=None, source_training_spec=original['name'])
    return case


def new_shifts(excluded, count=128):
    used = {tuple(row) for row in excluded}
    rows = []
    for counter in range(100000):
        b=hashlib.sha256(f'SETIsearch:M43AI:native-validation:v1:{counter}'.encode()).digest()
        row=(0,128+int.from_bytes(b[:8],'big')%3840,128+int.from_bytes(b[8:16],'big')%3840)
        if row in used or abs(row[1]-row[2]) < 128:
            continue
        used.add(row)
        rows.append(list(row))
        if len(rows)==count:
            return rows
    raise ValueError('Could not generate frozen disjoint shift inventory')


def design(original):
    cases=[translated_case(c,i) for i,c in enumerate(original['training_cases'])]
    excluded=original['previous_shift_rows']+original['training_native_shifts']+original['heldout_native_shifts']
    shifts=new_shifts(excluded)
    old_specs={json.dumps(c['components'],sort_keys=True) for c in original['training_cases']+original['validation_cases']}
    if any(json.dumps(c['components'],sort_keys=True) in old_specs for c in cases):
        raise ValueError('Prospective component specification overlaps a reserved panel')
    if len(cases)!=112 or sum(c['signal_present'] for c in cases)!=64:
        raise ValueError('Unexpected factorial-panel inventory')
    return dict(validation_cases=cases, native_null_shifts=shifts,
        excluded_shift_rows=sorted([list(r) for r in {tuple(r) for r in excluded}]),
        carrier_shift_channels=211, all_component_strength_scale=15/16,
        native_null_generation='SHA256 SETIsearch:M43AI:native-validation:v1:counter; big-endian first two uint64; 128+(value mod 3840); first 128 unique rows with |s1-s2|>=128 outside exclusions',
        old_reserved_validation_metadata_used_only_for_exclusion=True,
        old_reserved_validation_native_data_opened=False)
