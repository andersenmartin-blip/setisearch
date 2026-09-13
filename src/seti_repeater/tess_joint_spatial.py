"""LS7E closed-data prototype: empirical covariance and equal sparse fits.

These scores are engineering diagnostics, not probabilities. No LS7C code or
decision is changed. Only the optimal-aperture pixels enter the spatial fit.
"""
import numpy as np

from .light_sail_tess_v2 import pointing_delta, shifted_profile
from .light_sail_tess_v3 import empirical_profile


def event_difference(cube, start, stop):
    """The actual event mean minus two-sideband median; no white-noise scaling."""
    if not (60 <= start < stop <= len(cube)-60):
        raise ValueError("incomplete event/sideband context")
    side = np.concatenate((cube[start-60:start-5], cube[stop+5:stop+60]))
    if len(side) != 110 or not np.all(np.isfinite(side)):
        raise ValueError("invalid sidebands")
    ref = np.median(side, axis=0)
    delta = np.mean(cube[start:stop], axis=0)-ref
    if not np.all(np.isfinite(delta)):
        raise ValueError("invalid event")
    return delta, ref


def training_covariance(records, excluded_anchor, width, shrinkage):
    """Use other backgrounds only; retain all empirical vectors, without clipping."""
    chosen = [r for r in records if r["anchor"] != excluded_anchor and r["width"] == width]
    x = np.asarray([r["normalized_delta"] for r in chosen], dtype=float)
    if x.ndim != 2 or len(x) < 3 or not np.all(np.isfinite(x)) or not 0 < shrinkage <= 1:
        raise ValueError("invalid covariance training set")
    empirical = np.cov(x, rowvar=False, ddof=1)
    scale = float(np.trace(empirical)/len(empirical))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("degenerate empirical covariance")
    floor = 1e-10*scale
    result = ((1-shrinkage)*empirical + shrinkage*np.diag(np.diag(empirical))
              + floor*np.eye(len(empirical)))
    np.linalg.cholesky(result)
    return result, {"excluded_anchor": excluded_anchor, "width": width,
                    "training_anchors": sorted({r["anchor"] for r in chosen}),
                    "training_ids": [r["sample_id"] for r in chosen],
                    "samples": len(chosen), "shrinkage": shrinkage, "floor": floor,
                    "empirical_covariance": empirical.tolist(), "covariance": result.tolist(),
                    "eigenvalues": np.linalg.eigvalsh(result).tolist()}


def template_bank(reference, aperture, shifts, pointing_shifts):
    profile = empirical_profile(reference, aperture)
    stars = np.stack([shifted_profile(profile, aperture, s)[aperture] for s in shifts])
    nuisance, labels = [np.zeros(aperture.sum())], ["uniform"]
    for j in range(aperture.sum()):
        p = np.zeros(aperture.sum()); p[j] = 1
        nuisance.append(p); labels.append(f"pixel_{j}")
    for y in range(aperture.shape[0]-1):
        for x in range(aperture.shape[1]-1):
            p = np.zeros(aperture.shape); p[y:y+2, x:x+2] = 1
            if p[aperture].sum() > 0:
                nuisance.append(p[aperture]); labels.append(f"block2_{y}_{x}")
    for dy, dx in pointing_shifts:
        for sign in (1, -1):
            nuisance.append(sign*pointing_delta(reference, [dy, dx])[aperture])
            labels.append(f"pointing_{dy}_{dx}_{sign}")
    return stars, np.stack(nuisance), labels


class FitBank:
    """Nonnegative source, free uniform background, optionally one free pixel.

    The extra pixel has the same fixed objective penalty for every hypothesis.
    Enumerating the pixel is exact; no iterative outlier deletion is used.
    """
    def __init__(self, covariance, templates, sparse, penalty=9.):
        c = np.asarray(covariance, dtype=float)
        self.templates = np.atleast_2d(np.asarray(templates, dtype=float))
        n = c.shape[0]
        if (c.shape != (n, n) or n < 4 or self.templates.shape[1] != n
                or not np.all(np.isfinite(c)) or not np.all(np.isfinite(self.templates))
                or not np.allclose(c, c.T) or penalty < 0):
            raise ValueError("invalid fit inputs")
        np.linalg.cholesky(c)
        self.precision = np.linalg.inv(c)
        self.bases = [np.ones((n, 1))]
        if sparse:
            self.bases += [np.column_stack((np.ones(n), np.eye(n)[:, j])) for j in range(n)]
        self.projectors = []
        for b in self.bases:
            wb = self.precision @ b
            q = self.precision - wb @ np.linalg.solve(b.T @ wb, wb.T)
            self.projectors.append((q+q.T)/2)
        self.projectors = np.stack(self.projectors)
        self.norm = np.einsum('ti,sij,tj->st', self.templates, self.projectors, self.templates)
        tolerance = 1e-12*np.linalg.norm(self.precision, 2)*np.sum(self.templates**2, axis=1)
        self.valid = self.norm > tolerance[None, :]
        self.penalties = np.array([0.]+[penalty]*(len(self.bases)-1))

    def fit(self, delta):
        y = np.asarray(delta, dtype=float)
        if y.shape != (self.precision.shape[0],) or not np.all(np.isfinite(y)):
            raise ValueError("invalid event vector")
        py = self.projectors @ y
        cross = py @ self.templates.T
        amp = np.divide(np.maximum(cross, 0.), self.norm,
                        out=np.zeros_like(cross), where=self.valid)
        chi = np.maximum(0., (py @ y)[:, None]-amp*np.maximum(cross, 0.))
        objective = chi+self.penalties[:, None]
        s, t = np.unravel_index(np.argmin(objective), objective.shape)
        # Re-evaluate the winning residual directly, avoiding subtractive loss.
        b, p, a = self.bases[s], self.templates[t], float(amp[s, t])
        beta = np.linalg.solve(b.T @ self.precision @ b, b.T @ self.precision @ (y-a*p))
        residual = y-a*p-b @ beta
        raw = float(residual @ self.precision @ residual)
        return {"template_index": int(t), "sparse_pixel": None if s == 0 else int(s-1),
                "amplitude": a, "amplitude_noise_score": float(a*np.sqrt(max(0., self.norm[s, t]))),
                "background": float(beta[0]), "sparse_amplitude": None if s == 0 else float(beta[1]),
                "chi2": raw, "objective": raw+float(self.penalties[s]),
                "residual_dof": len(y)-1-len(beta)}


def diagnose(delta, star_fit, nuisance_fit, cfg):
    star, nuisance = star_fit.fit(delta), nuisance_fit.fit(delta)
    reduced = star["chi2"]/star["residual_dof"]
    margin = nuisance["objective"]-star["objective"]
    gates = {"source_amplitude": star["amplitude_noise_score"] >= cfg["source_score_min"],
             "weighted_residual": reduced <= cfg["reduced_chi2_max"],
             "nuisance_separation": margin >= cfg["nuisance_delta_chi2_min"]}
    return {"pass": bool(all(gates.values())), "gates": gates, "star": star,
            "nuisance": nuisance, "reduced_chi2": reduced, "nuisance_delta_chi2": margin}
