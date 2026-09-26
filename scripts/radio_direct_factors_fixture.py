"""Metadata and synthetic-native evidence for the direct eccentric interface."""
import gzip
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation,SkyCoord,solar_system_ephemeris
from astropy.time import Time
from astropy.utils import iers
from seti_repeater import factors_radio as direct, motion_radio as motion
from seti_repeater import search_v0p6 as core,transfer_m43g as native
from seti_repeater.exposure_radio import add_linear_exposure
from m43g_reference import sorted_reference,direct_reference

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_direct_factors_2026-09-26'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name,data):
    b=(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    (OUT/name).write_bytes(gzip.compress(b,mtime=0) if name.endswith('.gz') else b)


def inputs():
    cfg=json.loads((ROOT/'config/radio_direct_factors_engineering_20260926.json').read_text())
    audit=json.loads((ROOT/'config/radio_hd1461_motion_audit_20260926.json').read_text())
    runtime={key:importlib.metadata.version(key) for key in audit['runtime'] if key!='python'}
    runtime['python']=platform.python_version()
    if runtime!=audit['runtime']:raise ValueError('declared numerical runtime changed')
    source_path=ROOT/audit['preparation_contract']
    if sha(source_path)!=audit['preparation_contract_sha256']:raise ValueError('preparation contract changed')
    source=json.loads(source_path.read_text())
    result_path=ROOT/'results_radio_motion_2026-09-26/result.json'
    clock_path=ROOT/'results_radio_motion_2026-09-26/clock.json'
    result=json.loads(result_path.read_text())
    labels,starts,mids,ends=motion.integration_clock(source['scans'])
    clock=np.column_stack([(starts-mids[0]).sec,(mids-mids[0]).sec,(ends-mids[0]).sec])
    all_times=Time([t for triple in zip(starts,mids,ends) for t in triple])
    iers.conf.auto_download=False
    table=iers.IERS_B.open(iers.IERS_B_FILE)
    if sha(iers.IERS_B_FILE)!=result['iers_b_sha256']:raise ValueError('IERS evidence changed')
    if not np.all(table.ut1_utc(all_times,return_status=True)[1]==iers.FROM_IERS_B):raise ValueError('EOP coverage absent')
    if not np.all(table.pm_xy(all_times,return_status=True)[2]==iers.FROM_IERS_B):raise ValueError('polar motion coverage absent')
    site=audit['observatory']
    loc=EarthLocation.from_geodetic(site['longitude_deg']*u.deg,site['latitude_deg']*u.deg,site['height_m']*u.m)
    templates=[{'template_index':0,'projected_scale':0.,'phase_cycles':0.}]
    for scale in cfg['projected_scales']:
        for phase in np.arange(cfg['nonzero_phase_count'])/cfg['nonzero_phase_count']:
            templates.append({'template_index':len(templates),'projected_scale':scale,'phase_cycles':float(phase)})
    banks={};observers={}
    with iers.earth_orientation_table.set(table),solar_system_ephemeris.set('builtin'):
        for scenario in result['coordinate_scenarios']:
            if scenario['id'] not in cfg['coordinate_scenarios']:raise ValueError('unexpected coordinate scenario')
            sky=SkyCoord(scenario['ra_deg']*u.deg,scenario['dec_deg']*u.deg,frame='icrs')
            v=sky.radial_velocity_correction(obstime=all_times,location=loc).to_value(u.m/u.s).reshape(96,3)
            if not np.array_equal(v[:,1],scenario['midpoint_correction_m_s']):
                raise ValueError('retained observer midpoints changed')
            observer=1+v/motion.C_M_S
            provenance={'source_contract_sha256':sha(source_path),'clock_sha256':sha(clock_path),
                'observer_evidence_sha256':native.digest({'scenario':scenario,'edge_corrections_m_s':v.tolist(),
                    'iers_b_sha256':result['iers_b_sha256'],'parent_audit_sha256':sha(result_path)}),
                'coordinate_scenario':scenario['id'],'scan_labels':list(direct.LABELS)}
            bank=direct.build(clock_seconds=clock,observer_multipliers=observer,templates=templates,
                orbit=result['keplerian_comparison']['parameters'],provenance=provenance)
            banks[scenario['id']]=bank;observers[scenario['id']]=v.tolist()
    if set(banks)!=set(cfg['coordinate_scenarios']):raise ValueError('incomplete scenario inventory')
    return cfg,source,banks,observers


def independent_factors(bank):
    """Bisection and atan2 true anomaly, separate from the production Newton solver."""
    data=json.loads(bank.inputs_json);o=data['orbit'];e=o['eccentricity']
    times=np.asarray(data['clock_seconds']);observer=np.asarray(data['observer_multipliers'])
    output=[]
    k=2*np.pi*o['semi_major_axis_au']*149597870700/(o['period_days']*86400*np.sqrt(1-e*e))
    for t in data['templates']:
        mean=(2*np.pi*(times/(o['period_days']*86400)-t['phase_cycles'])+np.pi)%(2*np.pi)-np.pi
        low=np.full_like(mean,-np.pi);high=np.full_like(mean,np.pi)
        for _ in range(64):
            middle=(low+high)/2;above=middle-e*np.sin(middle)>=mean
            high=np.where(above,middle,high);low=np.where(above,low,middle)
        eccentric=(low+high)/2
        anomaly=2*np.arctan2(np.sqrt(1+e)*np.sin(eccentric/2),np.sqrt(1-e)*np.cos(eccentric/2))
        v=-t['projected_scale']*k*(np.cos(anomaly+np.deg2rad(o['omega_deg']))+e*np.cos(np.deg2rad(o['omega_deg'])))
        factor=observer*(1-v/299792458.)
        output.append(factor/factor[0,1])
    return np.asarray(output)


def run():
    OUT.mkdir(exist_ok=True)
    cfg,source,banks,observers=inputs()
    comparisons=[]
    for name,bank in banks.items():
        direct.validate(bank);reference=independent_factors(bank)
        error=float(np.abs(reference-bank.factors).max())
        if error>cfg['independent_factor_tolerance']:raise ValueError('independent eccentric oracle mismatch')
        comparisons.append({'scenario':name,'factor_bank_sha256':bank.identity,'factor_values':int(bank.factors.size),
            'maximum_independent_factor_error':error,'maximum_error_hz_at_1500_mhz':error*1.5e9})
    write('factor_banks.json.gz',{name:{'record':b.record(),'identity':b.identity,'factors':b.factors.tolist(),
            'observer_correction_m_s':observers[name]} for name,b in banks.items()})
    design=json.loads((ROOT/'results_radio_motion_2026-09-26/prospective_design.json').read_text())
    window=next(w for w in design['windows'] if w['role']=='validation')
    df=design['proposed_grid']['carrier_spacing_hz']
    grid=core.make_proxy_carrier_grid(window['proposed_first_on_midpoint_carrier_center_hz']/1e6,
        df,cfg['score_half_bins'],cfg['support_guard_bins'])
    geometry=core.NativeFrequencyGeometry(window['native_frequency_low_hz'],df,cfg['native_channels'])
    bank=banks[cfg['native_arithmetic_scenario']]
    rng=np.random.default_rng(cfg['raw_seed']);records=[];sampled_scores={};normalization_cells=0;score_cells=0
    for si,label in enumerate(direct.LABELS):
        raw=np.asarray(cfg['raw_background_mean']+cfg['raw_background_sigma']*rng.standard_normal((16,cfg['native_channels'])),dtype='<f4')
        if label.endswith('_on'):
            starts=direct.for_scan(bank,label,sample='start')[cfg['injection_template_index']]
            ends=direct.for_scan(bank,label,sample='end')[cfg['injection_template_index']]
            a=(grid.center_mhz*1e6*starts-geometry.raw_zero_hz)/df
            b=(grid.center_mhz*1e6*ends-geometry.raw_zero_hz)/df
            raw=add_linear_exposure(raw,a,b,intrinsic_width_channels=cfg['injection_intrinsic_width_channels'],
                total_power=cfg['injection_total_digital_power_per_row'])
        src=native.normalize_synthetic_rows(lambda row:raw[row],geometry,16,input_orientation='ascending',
            scope={'kind':'synthetic','scan':label,'direct_factor_bank_sha256':bank.identity,
                   'fixture_seed':cfg['raw_seed'],'injection_before_normalization':True})
        reference_normalized=sorted_reference(raw)
        if not np.array_equal(src.values.view('<u4'),reference_normalized.view('<u4')):raise ValueError('normalization oracle mismatch')
        normalization_cells+=raw.size
        for width in cfg['spectral_widths']:
            cache=direct.synthetic_cache(src,bank,label,grid,width)
            actual=native.gather_bank_slice(cache,0,grid.support_bin_count,chunk_bins=cfg['score_chunk_bins'])
            expected=direct_reference(reference_normalized,geometry,direct.for_scan(bank,label),grid,width,0,grid.support_bin_count)
            if not np.array_equal(actual.view('<u4'),expected.view('<u4')):raise ValueError('native full-bank score mismatch')
            score_cells+=actual.size
            records.append({'scan':label,'width':width,'source_identity':src.identity,'cache_identity':cache.identity,
                'score_sha256':native.array_hash(actual),'oracle_sha256':native.array_hash(expected),'shape':list(actual.shape),
                'all_score_cells_bit_exact':True,'complete_support_covered':True,
                'center_carrier_scores_all_templates':actual[:,grid.support_guard_bins+cfg['score_half_bins']].tolist()})
            if label=='epoch1_on' and width in (1,65):sampled_scores[str(width)]=actual.tolist()
    write('native_score_receipts.json',{'records':records,'normalization_cells_bit_exact':normalization_cells,
        'full_support_score_cells_bit_exact':score_cells,'full_matrices_persisted':'epoch1_on, widths 1 and 65; all remaining full matrices are reproducible from the fixed generator and have retained exact oracle hashes'})
    write('native_scores_selected.json.gz',sampled_scores)
    result={'schema':'radio-direct-factor-qualification-v1','status':'DIRECT_FACTORS_AND_SYNTHETIC_NATIVE_ARITHMETIC_PASS',
        'coordinate_scenarios':comparisons,'templates_per_scenario':bank.template_count,
        'factor_samples_per_integration':3,'source_telescope_requests':0,'real_spectral_values_read':False,
        'normalization_cells_bit_exact':normalization_cells,'score_cells_bit_exact':score_cells,
        'native_scenarios_evaluated':[cfg['native_arithmetic_scenario']],
        'runtime':json.loads((ROOT/'config/radio_hd1461_motion_audit_20260926.json').read_text())['runtime'],
        'native_width_scan_arrays':len(records),'native_source_realizations':1,
        'source_pointing_resolved':False,'full_detector_connected':False,'scientific_recovery_measured':False,
        'calibration_transfer_qualified':False,'physical_model_qualified':False,
        'working_model':'first-order eccentric relative-phase model; no absolute ephemeris or relativistic accuracy qualification',
        'preserved_legacy_files_sha256':{p:sha(ROOT/p) for p in ('src/seti_repeater/search_v0p6.py','src/seti_repeater/detector_m43u.py',
            'src/seti_repeater/pipeline_radio.py','src/seti_repeater/transfer_m43g.py','src/seti_repeater/source_radio.py',
            'config/radio_hd1461_source_preparation_20260926.json')}}
    write('result.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
