"""Display every native order covering H04/H10; descriptive post-hoc inspection."""
from pathlib import Path
import json, tarfile, io, subprocess
import numpy as np
from astropy.io import fits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'triage_followup/native'
records=json.loads((OUT/'MAPPING.json').read_text())
products=json.loads((BASE/'triage_followup/products/MANIFEST.json').read_text())['products']
extra=[]
for m in records:
    if len(m['possible_orders'])<2: continue
    hid=m['hit_id']
    rawrec=next(p for p in products if p['hit_id']==hid and p['kind']=='RAW')
    tarrec=next(p for p in products if p['hit_id']==hid and p['kind']=='ANCILLARY')
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rawrec['relative_path'])],capture_output=True,check=True).stdout)) as h:
        raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
    with tarfile.open(BASE/tarrec['relative_path']) as t:
        member=next(p for p in t if p.name.endswith('_e2ds_A.fits'))
        with fits.open(io.BytesIO(t.extractfile(member).read())) as h:
            native=h[0].data.astype(float);hdr=h[0].header.copy()
    fig,axs=plt.subplots(len(m['possible_orders']),2,figsize=(10,6),layout='constrained')
    for j,o in enumerate(m['possible_orders']):
        degree=hdr['ESO DRS CAL TH DEG LL'];ldeg=hdr['ESO DRS CAL LOC DEG CTR']
        wave=np.polynomial.polynomial.polyval(np.arange(4096),[hdr['ESO DRS CAL TH COEFF LL'+str(o*(degree+1)+i)] for i in range(degree+1)])
        k=int(np.argmin(abs(wave-m['topocentric_air_estimate_angstrom'])))
        cy=4095-k
        cx=float(np.polynomial.polynomial.polyval(cy,[hdr['ESO DRS CAL LOC CTR'+str(o*(ldeg+1)+i)] for i in range(ldeg+1)]))
        ix=round(cx);cut=raw[cy-10:cy+11,ix-9:ix+10]
        assert cut.shape==(21,19)
        sl=slice(k-15,k+16)
        np.savez_compressed(OUT/f'{hid}_order{o}_cutout.npz',raw_cutout=cut,native_wave=wave[sl],native_flux=native[o,sl])
        axs[j,0].plot(wave[sl],native[o,sl],'.-');axs[j,0].axvline(m['topocentric_air_estimate_angstrom'],c='red',ls='--')
        axs[j,0].set_title(f'{hid} {m["target"]} native order {o}')
        axs[j,1].imshow(cut,origin='lower',aspect='auto',cmap='magma',extent=[-9.5,9.5,-10.5,10.5]);axs[j,1].axhline(0,c='cyan',lw=.6);axs[j,1].axvline(cx-ix,c='cyan',lw=.6)
        axs[j,1].set_title('Raw CCD, linear scale')
        extra.append(dict(hit_id=hid,order=o,native_pixel=k,raw_row=cy,raw_column=cx,cutout=f'{hid}_order{o}_cutout.npz',interpretation='Descriptive overlap follow-up; no detector change or automatic veto.'))
    axs[-1,0].set_xlabel('Approximate topocentric air wavelength (Å)');axs[-1,1].set_xlabel('Cross-dispersion pixel offset')
    fig.savefig(OUT/f'{hid}_OVERLAPPING_ORDERS.png',dpi=110);plt.close(fig)
(OUT/'OVERLAP_MAPPING.json').write_text(json.dumps(extra,indent=2)+'\n')
print(json.dumps(extra,indent=2))

# Compact pages of all ten previously mapped cutouts, without re-selection.
for start in [0,5]:
    fig,axs=plt.subplots(5,2,figsize=(10,11),layout='constrained')
    for j,m in enumerate(records[start:start+5]):
        d=np.load(OUT/(m['hit_id']+'_cutout.npz'))
        axs[j,0].plot(d['native_wave'],d['native_flux'],'.-')
        axs[j,0].axvline(m['topocentric_air_estimate_angstrom'],color='red',ls='--')
        axs[j,0].set_title(m['hit_id']+' '+m['target'])
        axs[j,1].imshow(d['raw_cutout'],origin='lower',aspect='auto',cmap='magma',extent=[-9.5,9.5,-10.5,10.5])
        axs[j,1].axhline(0,c='cyan',lw=.6)
        axs[j,1].axvline(m['trimmed_raw_column_float']-round(m['trimmed_raw_column_float']),c='cyan',lw=.6)
        axs[j,1].set_title('Raw CCD, linear scale')
    axs[-1,0].set_xlabel('Topocentric air wavelength (Å)')
    axs[-1,1].set_xlabel('Cross-dispersion pixel offset')
    fig.savefig(OUT/f'RAW_REVIEW_{start+1:02}_{start+5:02}.png',dpi=100);plt.close(fig)
