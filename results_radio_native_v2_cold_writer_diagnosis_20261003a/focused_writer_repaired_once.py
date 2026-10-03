"""Run exactly one unchanged focused tiny unittest after the observer repair."""
from pathlib import Path

baseline = Path(__file__).with_name('focused_writer_diagnosis.py')
source = baseline.read_text().replace('range(12)', 'range(2, 3)')
source = source.replace('focused-writer-summary.json', 'focused-writer-repaired-summary.json')
exec(compile(source, str(baseline), 'exec'), globals())
