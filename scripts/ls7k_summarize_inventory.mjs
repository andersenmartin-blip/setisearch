import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

export function summarize(inventory) {

const header = h => Object.fromEntries(h.cards.map(c => [c.key, c.value]));
const sectors = inventory.light_curves.map(lc => {
  const models = inventory.prf_models.filter(m => m.sector === lc.sector);
  const checks = models.map(m => {
    const a = header(m.hdus[0]), b = header(m.hdus[1]);
    return a.VERSION === "UPDATED_2.0" && a.DATATYPE === "PRF" && b.DATATYPE === "Uncertainties" &&
      [a,b].every(h => h.CAM === lc.camera && h.CCD === lc.ccd && h.NSAMP === 9 &&
        h.CCD_RREF === m.grid_row && h.CCD_CREF === m.grid_col &&
        h.CRVAL1P === m.grid_col && h.CRVAL2P === m.grid_row &&
        h.CRPIX1P === 59 && h.CRPIX2P === 59 &&
        Math.abs(h.CDELT1P - 1/9) < 1e-14 && Math.abs(h.CDELT2P - 1/9) < 1e-14 &&
        h.CTYPE1P === "RAWX" && h.CTYPE2P === "RAWY");
  });
  const sums = models.map(m => m.hdus[0].array.sum);
  return {
    sector: lc.sector, camera: lc.camera, ccd: lc.ccd,
    timing_rows: lc.selected_rows,
    time_correction_seconds_range: [lc.time_correction_seconds.min, lc.time_correction_seconds.max],
    frames_per_cadence: lc.metadata.NUM_FRM,
    integration_seconds_per_frame: lc.metadata.INT_TIME,
    read_seconds_per_frame: lc.metadata.READTIME,
    nominal_integration_seconds_per_cadence: lc.metadata.NUM_FRM * lc.metadata.INT_TIME,
    nominal_cadence_seconds: lc.metadata.TIMEDEL * 86400,
    nominal_target_detector_xy: lc.geometry.nominal_target_detector_xy,
    cutout_detector_corners_xy: lc.geometry.corners_detector_xy,
    prf_count: models.length,
    prf_bytes: models.reduce((n,m) => n+m.bytes,0),
    prf_and_uncertainty_values: models.reduce((n,m) => n+m.hdus.reduce((z,h) => z+h.array.values,0),0),
    header_contract_checks_passed: checks.filter(Boolean).length,
    prf_sum_range: [Math.min(...sums), Math.max(...sums)],
    prf_negative_values: models.reduce((n,m) => n+m.hdus[0].array.negative,0),
    uncertainty_negative_values: models.reduce((n,m) => n+m.hdus[1].array.negative,0),
    missing_motion_uncertainty_columns: lc.missing_motion_uncertainty_columns
  };
});
if (sectors.length !== 2 || sectors.some(s => s.prf_count !== 25 || s.header_contract_checks_passed !== 25))
  throw new Error("Calibration header identity/geometry contract failed");
return {
  study: "LS7K",
  derivation: "Post-acquisition summary of the sealed inventory only; no fitted response or detector outcome.",
  input_inventory_sha256: "df6557c807c4cbf09c3b97d92af411041d367e6357ef5998666c7c24fcc6a306",
  input_result_commit: "f1ce03ec5f278a8850125a169a98490ba2cfa204",
  sectors,
  total_prf_bytes: sectors.reduce((n,s) => n+s.prf_bytes,0),
  total_prf_and_uncertainty_values: sectors.reduce((n,s) => n+s.prf_and_uncertainty_values,0),
  engineering_links: inventory.engineering.selected_links,
  readiness: {
    timing_extracts: "verified",
    nominal_science_wcs: "verified",
    mission_prf_files_and_internal_wcs: "verified",
    prf_to_science_absolute_coordinate_relation: "not yet established",
    engineering_sample_time_reference_and_coverage: "not inspected",
    fast_pos_corr_temporal_kernel_and_covariance: "not established",
    upstream_target_exclusion: "not established",
    forward_model_benchmark: "inputs available; specification still required",
    detector_qualification: "not ready"
  }
};
}

const path = process.argv[2] || 'results_ls7k_inputs/inventory.json';
const bytes = readFileSync(path);
const result = summarize(JSON.parse(bytes.toString('utf8')));
if (createHash('sha256').update(bytes).digest('hex') !== result.input_inventory_sha256)
  throw new Error('Sealed inventory hash changed');
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
