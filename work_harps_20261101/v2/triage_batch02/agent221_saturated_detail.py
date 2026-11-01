"""Display faint structure under bright pixels; no array/fit/classification edits."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
mapping = json.loads((OUT / 'NATIVE_MAPPING.json').read_text())
fig, axs = plt.subplots(2, 2, figsize=(8,6), layout='constrained')
for row, i in enumerate([267,285]):
    orders = [x for x in mapping['orders'] if x['review_id'] == f'V2-{i:04d}' and x['status'] == 'EXTRACTED']
    for col, x in enumerate(orders):
        d = np.load(OUT / x['cutout'])
        excess = np.maximum(d['raw_excess'][:,6:19],0)
        vmax = np.percentile(excess,95)
        axs[row,col].imshow(excess, origin='lower', aspect='auto', vmin=0, vmax=vmax,
                            cmap='magma', extent=[-6.5,6.5,-10.5,10.5])
        axs[row,col].axvline(x['raw_column']-round(x['raw_column']), color='cyan', lw=.6)
        axs[row,col].axhline(0, color='cyan', lw=.6)
        axs[row,col].set_title(f'V2-{i:04d}, order {x["order"]}; vmax={vmax:.1f}')
fig.suptitle('Positive raw excess, saturation at the 95th percentile\nShows faint structure obscured by bright off-center pixels; arrays unchanged')
fig.savefig(OUT / 'figures/AGENT221_DETAIL_SATURATED.png',dpi=110)
