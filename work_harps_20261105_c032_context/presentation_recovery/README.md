# Preserved presentation integrity failure

After the original complete plot index was recorded, the native figure differed
from its recorded hash and was truncated at a PNG IDAT checksum. The cause is
unknown. The changed bytes are preserved as ATTEMPT01_NATIVE_ORDERS_1.png.failed,
with the original index and validation result.

The other three figures matched their recorded hashes and decoded correctly.
The identical frozen plot_group.py was rerun against unchanged numerical outputs.
All four resulting figures decode and match all four originally recorded hashes,
including the native figure. No numerical production execution, fit, plot rule or
scientific variant was added. See RECOVERY_RECEIPT.json for exact identities.

The failed byte file is intentionally invalid evidence, not a deliverable figure.
The four scientific figures under analysis/results/figures are the verified copies.
