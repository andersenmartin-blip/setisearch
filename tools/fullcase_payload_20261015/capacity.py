"""Pure arithmetic admission; never consumes or resets a closed ledger."""


def preadmit(case_bound_bytes, slots, output_limit_bytes, *, mode):
    if mode != 'ENGINEERING_COMPARISON_ONLY':
        raise ValueError('No scientific resource admission implemented')
    if any(type(v) is not int or v < 0 for v in (case_bound_bytes, slots, output_limit_bytes)):
        raise ValueError('Nonnegative integer byte/slot values required')
    if case_bound_bytes == 0: raise ValueError('Positive case bound required')
    required = case_bound_bytes * slots
    return {'status': 'ARITHMETIC_FITS_ONLY' if required <= output_limit_bytes else 'NOT_ADMITTED_CAPACITY',
            'requested_slots': slots, 'per_case_conditional_cap_bytes': case_bound_bytes,
            'all_slots_at_cap_bytes': required, 'comparison_limit_bytes': output_limit_bytes,
            'max_slots_at_cap': output_limit_bytes // case_bound_bytes,
            'scientific_admission': False, 'any_ledger_read_or_mutated': False,
            'production_launched': False}
