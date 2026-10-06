"""Exact, metadata-only HDF5 filter-pipeline admission before payload reads."""


def _integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(label+' must be a nonnegative integer')
    return value


def signature(filters):
    if not isinstance(filters, (list, tuple)):
        raise ValueError('Filter pipeline must be an explicit list')
    result=[]
    for item in filters:
        if not isinstance(item, (list, tuple)) or len(item) not in (3,4):
            raise ValueError('Filter entry requires ID, flags and client data')
        filter_id=_integer(item[0], 'Filter ID')
        flags=_integer(item[1], 'Filter flags')
        if not isinstance(item[2], (list, tuple)):
            raise ValueError('Filter client data must be explicit')
        values=[_integer(x, 'Filter client datum') for x in item[2]]
        result.append([filter_id, flags, values])
    return result


def declared(definition, *, required):
    if 'observed_hdf5_filters' not in definition:
        if required:
            raise ValueError('Telescope filter declaration required before access')
        return None
    return signature(definition['observed_hdf5_filters'])


def check_dataset(dataset, expected):
    """Inspect creation metadata only; do not index/read the dataset."""
    if expected is None:
        return None
    expected=signature(expected)
    creation=dataset.id.get_create_plist()
    observed=signature([creation.get_filter(i) for i in range(creation.get_nfilters())])
    if observed != expected:
        raise ValueError('HDF5 filter pipeline differs from source declaration')
    return observed
