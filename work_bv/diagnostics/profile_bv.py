"""Descriptive profiles from closed BU/BV summaries; no new signal search."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import io
import json
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def build_profiles():
    inputs=[]; profiles=[]; identities=None
    for stage,count in [('bu',4),('bv',28)]:
        planpath=ROOT/f'work_{stage}/{stage.upper()}_PARTIAL_PLAN.json'
        plan=read(planpath); plan_digest=sha(planpath)
        scans=plan['scans']
        current=[{k:s[k] for k in ('scan','role','target','archive_id')} for s in scans]
        assert identities is None or identities==current
        identities=current
        for batch in range(1,count+1):
            folder=ROOT/f'work_{stage}/execution/batch{batch}'
            resultpath=folder/'payload/RESULT.json'; capture=read(folder/'ACTUAL_RECEIPT.json')
            result=read(resultpath); archivepath=folder/'payload/EVIDENCE.zip'
            assert result['status']==capture['status']=='PASS'
            assert capture['actual_exit_code']==0 and capture['stdout_eof']
            assert sha(resultpath)==capture['result_sha256']
            archive_digest=sha(archivepath)
            assert archive_digest==result['archive']['sha256']
            with zipfile.ZipFile(archivepath) as archive:
                manifest=json.loads(archive.read('ARCHIVE_MANIFEST.json'))
                record=next(m for m in manifest['members'] if m['path']=='BATCH_COMPLETE.json')
                payload=archive.read('BATCH_COMPLETE.json')
                assert len(payload)==record['bytes'] and hashlib.sha256(payload).hexdigest()==record['sha256']
                complete=json.loads(payload)
            assert complete['plan_sha256']==plan_digest
            assert complete['q_list']==plan['batch_q_lists'][batch-1]
            assert [q['q'] for q in complete['results']]==complete['q_list']
            inputs.append(dict(stage=stage.upper(),batch=batch,archive_path=str(archivepath.relative_to(ROOT)),
                               archive_sha256=archive_digest,archive_bytes=archivepath.stat().st_size,
                               summary_member='BATCH_COMPLETE.json',summary_sha256=record['sha256'],
                               plan_path=str(planpath.relative_to(ROOT)),plan_sha256=plan_digest,
                               process_result_sha256=sha(resultpath)))
            for q in complete['results']:
                assert [s['scan'] for s in q['scans']]==list(range(5))
                first=scans[0]['fch1_mhz'];df=scans[0]['df_hz']/1e6
                low=first+((q['q']+1)*4096-1)*df;high=first+q['q']*4096*df
                rows=[]
                for scan in q['scans']:
                    widths=scan['width_searches'];assert [w['width_channels'] for w in widths]==[1,3,9,33]
                    scores=[w['maximum_local_ess'] for w in widths]
                    assert np.isfinite(scores).all()
                    rows.append(dict(scan=scan['scan'],maximum_local_ess=max(scores),
                                     local_catalog_rows=scan['local_hits'],width_maxima=[
                                         dict(width_channels=w['width_channels'],maximum_local_ess=w['maximum_local_ess']) for w in widths]))
                profiles.append(dict(stage=stage.upper(),batch=batch,q=q['q'],
                                     frequency_midpoint_mhz=(low+high)/2,frequency_low_mhz=low,
                                     frequency_high_mhz=high,scans=rows))
    assert [p['q'] for p in profiles]==list(range(1,254))
    peaks=[p['q'] for p in profiles if max(s['maximum_local_ess'] for s in p['scans'])>=10]
    data=dict(schema='SETI_BU_BV_DESCRIPTIVE_SCORE_PROFILES_V1',
                created_utc=datetime.now(timezone.utc).isoformat(),source_sha256=sha(Path(__file__)),
                derivation='Read maxima over all drift rates and widths from authenticated closed BATCH_COMPLETE summaries. No new search, normalization, score or classification was computed.',
                scan_identities=identities,inputs=inputs,profiles=profiles,
                total_q=253,technical_channel_bin_width_mhz=253*4096*2.7939677238464355/1e6,
                q_with_any_scan_maximum_at_least_10=peaks,
                maximum_local_ess=max(s['maximum_local_ess'] for p in profiles for s in p['scans']),
                interpretation='Descriptive local ESS, not sigma or calibrated FAP; original detection threshold10 unchanged. Missing OFF5 prevents full-cadence qualification.',
                posthoc_visualization=True,classification_changes=False,new_signal_searches=0,
                complete_OFF_support=False,missing_scan=5,original_coverage_credit=0)
    data['carrier_zoom']=build_carrier_zoom(data)
    return data


def build_carrier_zoom(data):
    """Read stored drift maxima at actual centers; never evaluate a track."""
    center_mhz=2300.390625;half_range_hz=1000
    plan=read(ROOT/'work_bv/BV_PARTIAL_PLAN.json');scope=plan['scans'][0]
    reference_native=(center_mhz-scope['fch1_mhz'])*1e6/scope['df_hz']
    assert reference_native==524288
    pieces={i:[] for i in range(5)};bindings=[]
    for profile in data['profiles']:
        q=profile['q']
        if (profile['frequency_high_mhz']<center_mhz-half_range_hz/1e6
                or profile['frequency_low_mhz']>center_mhz+half_range_hz/1e6):
            continue
        stage=profile['stage'].lower();batch=profile['batch']
        archivepath=ROOT/f'work_{stage}/execution/batch{batch}/payload/EVIDENCE.zip'
        with zipfile.ZipFile(archivepath) as archive:
            manifest=json.loads(archive.read('ARCHIVE_MANIFEST.json'))
            members={m['path']:m for m in manifest['members']}
            for scan in range(5):
                member=f'q{q:03d}/scan{scan}_grid.npz';payload=archive.read(member)
                digest=hashlib.sha256(payload).hexdigest();assert digest==members[member]['sha256']
                bindings.append(dict(archive_path=str(archivepath.relative_to(ROOT)),member=member,sha256=digest))
                centers=np.arange(q*4096,(q+1)*4096,dtype=np.int32)
                best=np.full(len(centers),-np.inf)
                with np.load(io.BytesIO(payload),allow_pickle=False) as grid:
                    for width in (1,3,9,33):
                        searched=grid[f'centers_width_{width}'];scores=grid[f'max_ess_width_{width}']
                        assert len(searched)==len(scores) and np.isfinite(scores).all()
                        indices=searched-q*4096
                        assert (indices>=0).all() and (indices<len(centers)).all()
                        best[indices]=np.maximum(best[indices],scores)
                assert np.isfinite(best).all()
                delta_hz=(centers-reference_native)*scope['df_hz']
                mask=np.abs(delta_hz)<=half_range_hz
                pieces[scan].extend(dict(native_center=int(c),offset_hz=float(d),maximum_stored_local_ess=float(v))
                                    for c,d,v in zip(centers[mask],delta_hz[mask],best[mask]))
    result=[]
    for scan,rows in pieces.items():
        rows.sort(key=lambda x:x['offset_hz'])
        assert len({r['native_center'] for r in rows})==len(rows)
        result.append(dict(scan=scan,points=rows))
    return dict(reference_frequency_mhz=center_mhz,half_range_hz=half_range_hz,source_grid_members=bindings,scans=result,
                derivation='At each actual stored carrier center, maximum of stored per-width drift maxima only for widths searched at that center. No interpolation or new drift/track calculation.',
                display_warning='Maximization over drift rates broadens profiles; these curves are not single-drift line widths.')


def draw(data):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,
                         'axes.labelsize':10,'svg.fonttype':'none','axes.edgecolor':'#778391'})
    fig,axes=plt.subplots(2,1,figsize=(12,8.5),gridspec_kw={'height_ratios':[1.25,1]})
    fig.subplots_adjust(left=.085,right=.975,top=.80,bottom=.145,hspace=.39)
    profiles=data['profiles'];x=np.array([p['frequency_midpoint_mhz'] for p in profiles]);order=np.argsort(x)
    colors=['#174d77','#db8b00','#00877c','#cf3d45','#7f55a6']
    q_above=data['q_with_any_scan_maximum_at_least_10']
    selected=[p for p in profiles if p['q'] in q_above]
    for ax in axes:
        for identity,color in zip(data['scan_identities'],colors):
            i=identity['scan'];role=identity['role']
            if ax is axes[0]:
                xx=x[order];y=np.array([p['scans'][i]['maximum_local_ess'] for p in profiles])[order]
            else:
                points=data['carrier_zoom']['scans'][i]['points']
                xx=np.array([p['offset_hz'] for p in points]);y=np.array([p['maximum_stored_local_ess'] for p in points])
            ax.plot(xx,y,color=color,linestyle='-' if role=='ON' else '--',
                    linewidth=1.6 if role=='ON' else 1.8,label=f'{role} {i} · {identity["target"]}',
                    alpha=.9)
        ax.axhline(10,color='#384554',linewidth=1.2,linestyle=(0,(2,3)),zorder=0)
        ax.set_yscale('log');ax.set_ylim(3,50000)
        ax.set_yticks([5,10,100,1000,10000])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y,pos:f'{int(y):,}'.replace(',','.')))
        ax.set_ylabel('Maksimal lokal ESS (log-skala)')
        ax.grid(axis='y',which='major',color='#dfe4e8',linewidth=.7)
        ax.grid(axis='x',color='#edf0f3',linewidth=.6)
        ax.spines[['top','right']].set_visible(False)
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{v:.3f}'.replace('.',',')))
    axes[0].axvspan(min(p['frequency_low_mhz'] for p in selected),max(p['frequency_high_mhz'] for p in selected),
                   facecolor='#e7ebef',alpha=.5,zorder=-1)
    axes[0].set_xlim(min(p['frequency_low_mhz'] for p in profiles),max(p['frequency_high_mhz'] for p in profiles))
    axes[0].set_title('Hele det analyserede frekvensudsnit',loc='left',fontweight='bold',pad=10)
    axes[0].set_xlabel('Frekvens ved midtpunktet af hvert q-udsnit (MHz)',labelpad=7)
    axes[0].text(.995,.17,'Fast tærskel: 10',transform=axes[0].transAxes,ha='right',color='#384554',fontsize=9,
                 bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':2})
    axes[1].set_xlim(-1000,1000)
    axes[1].axvline(0,color='#718091',linewidth=1,linestyle=':',zorder=0)
    axes[1].set_title('Gemte bærefrekvenser: stærkt fælles spor i mål og kontroller',loc='left',fontweight='bold',pad=10)
    axes[1].set_xlabel('Bærefrekvens − 2300,390625 MHz (Hz)',labelpad=9)
    fig.text(.085,.948,'HIP44295: scoreprofil for mål og kontroller',fontsize=19,fontweight='bold',color='#1b2d3f')
    fig.text(.085,.914,'253 udsnit · 3 målscanninger (ON) + 2 kontrolscanninger (OFF) · samlet 2,895 MHz',fontsize=11,color='#516171')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.079,.888),ncol=5,frameon=False,
               columnspacing=1.3,handlelength=2.3,fontsize=9)
    fig.text(.085,.077,'Øverst: maksimum pr. 11,44 kHz ved q-midtpunkter. Nederst: gemte driftmaksima ved faktiske bærefrekvenser.',fontsize=8.5,color='#516171')
    fig.text(.085,.049,'Maksimum over drift udvider profilerne. ESS er ikke sigma/FAP. Tredje OFF-scanning (scan 5) er ufuldstændig.',fontsize=8.5,color='#516171')
    fig.savefig(OUT/'ESS_PROFILE_BU_BV.svg',facecolor='white')
    fig.savefig(OUT/'ESS_PROFILE_BU_BV.png',dpi=180,facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    data=build_profiles()
    path=OUT/'PROFILES_BU_BV.json'
    with path.open('w') as stream:json.dump(data,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    draw(data)
    print(json.dumps({k:data[k] for k in ['total_q','maximum_local_ess','q_with_any_scan_maximum_at_least_10','technical_channel_bin_width_mhz']}))
