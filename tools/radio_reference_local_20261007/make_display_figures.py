#!/usr/bin/env python3
"""Presentation only: replot pinned reference values; never invoke detector.

Original frozen plots and all scientific outputs remain byte-for-byte unchanged.
Frequency labels use kHz offsets; dB labels use explicit decimal formatting.
"""
from pathlib import Path
import hashlib, json, resource, time
START=time.monotonic(); CPU=time.process_time()
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MultipleLocator

P=Path(__file__).resolve().parent
R=P/"results"
config=json.loads((P/"config.json").read_text())
header=json.loads((R/"header.json").read_text())
coverage=json.loads((R/"coverage.json").read_text())
manifest=json.loads((R/"result_manifest.json").read_text())
for f,v in manifest["files"].items():
    assert hashlib.sha256((R/f).read_bytes()).hexdigest()==v["sha256"]
src=P/"Voyager1.single_coarse.fine_res.fil"
assert hashlib.sha256(src.read_bytes()).hexdigest()==config["source_sha256"]
h=header["header"]
raw=np.memmap(src,mode="r",dtype="<f4",offset=header["data_offset"],shape=(header["n_time_rows"],1,h["nchans"]))
idx=np.arange(coverage["search_first_channel"],coverage["search_last_channel"]+1)
freq=h["fch1"]+idx*h["foff"]
power=np.asarray(raw[:,0,idx],dtype=float)
t=np.arange(header["n_time_rows"])*h["tsamp"]
base_mhz=8419.297
offset=(freq-base_mhz)*1000
spectrum=10*np.log10(power.mean(axis=0))
cp=np.flatnonzero((freq>=config["carrier_plot_mhz"][0])&(freq<=config["carrier_plot_mhz"][1]))
x=offset[cp][::-1]
image=(10*np.log10(power[:,cp]))[:,::-1]

def spectrum_panel(ax):
    ax.plot(offset,spectrum,lw=.65,color="#1f6eaa")
    ax.set(xlabel="Frequency offset from 8419.297 MHz (kHz)",ylabel="Mean power (arbitrary dB)")
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.grid(alpha=.17)

def waterfall_panel(ax,fig):
    m=ax.imshow(image,origin="lower",aspect="auto",extent=[x[0]-abs(h["foff"])*1000/2,x[-1]+abs(h["foff"])*1000/2,-h["tsamp"]/2,t[-1]+h["tsamp"]/2],cmap="viridis",vmin=np.percentile(image,5),vmax=np.percentile(image,99.8))
    ax.set(xlabel="Frequency offset from 8419.297 MHz (kHz)",ylabel="Time since first midpoint (s)")
    ax.xaxis.set_major_locator(MultipleLocator(.5))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    fig.colorbar(m,ax=ax,label="Power (arbitrary dB)")

fig,ax=plt.subplots(figsize=(10,4),constrained_layout=True)
spectrum_panel(ax)
ax.set_title("GBT Voyager 1 reference — 19 September 2016\nPresentation only: carrier and two telemetry sidebands")
fig.savefig(R/"reference_spectrum_display.png",dpi=150); plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5),constrained_layout=True)
waterfall_panel(ax,fig)
ax.set_title("GBT Voyager 1 reference — known carrier\nPresentation only; no new search or validation")
fig.savefig(R/"reference_waterfall_display.png",dpi=150); plt.close(fig)
fig,(a,b)=plt.subplots(2,1,figsize=(10,8),constrained_layout=True,gridspec_kw={"height_ratios":[1,1.35]})
spectrum_panel(a); a.set_title("Known Voyager carrier and telemetry sidebands")
waterfall_panel(b,fig); b.set_title("Carrier drift in the original telescope reference")
fig.suptitle("GBT · Voyager 1 · 19 September 2016\nDisplay of retained engineering reference, not a SETI finding",fontsize=14)
fig.savefig(R/"reference_display.png",dpi=150); plt.close(fig)

# Prove the exact original frozen output manifest still holds after formatting.
for f,v in manifest["files"].items():
    assert hashlib.sha256((R/f).read_bytes()).hexdigest()==v["sha256"]
r=resource.getrusage(resource.RUSAGE_SELF)
receipt={"role":"presentation_only_no_detector_invocation","wall_s":time.monotonic()-START,"cpu_s":time.process_time()-CPU,
         "peak_rss_bytes":int(r.ru_maxrss)*1024,"original_outputs_unchanged":True,
         "source_sha256":config["source_sha256"],"frequency_reference_mhz":base_mhz,
         "power_transform":"Exactly 10*log10(linear power), matching the original frozen plot; explicit decimal y tick labels",
         "original_units":"Original code already used dB correctly; display formatting clarified labels and kHz frequency offsets",
         "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(R/"display_resource_receipt.json").write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
