"""LS7N effective cadence response; no subcadence attitude reconstruction."""
import numpy as np

MAD=1.482602218505602


def side_indices(start,stop):
    if not 60<=start<stop<=341:raise ValueError('incomplete protected window')
    return np.r_[start-60:start-5,stop+5:stop+60]


def plane_basis(shape):
    y,x=np.indices(shape,dtype=float)
    return np.stack([np.ones_like(x),(y-5)/5,(x-5)/5],axis=-1)


def side_state(cube,aperture,start,stop,support=None):
    side=side_indices(start,stop)
    if cube.shape!=(401,11,11) or not np.isfinite(cube[side]).all():raise ValueError('invalid sideband cube')
    left,right=cube[start-60:start-5],cube[stop+5:stop+60]
    differences=np.concatenate([np.diff(left,axis=0),np.diff(right,axis=0)])
    noise=MAD*np.median(abs(differences-np.median(differences,axis=0)),axis=0)/np.sqrt(2)
    variance=noise**2
    support=np.ones((11,11),bool) if support is None else support
    positive=variance[support&(variance>0)]
    if not positive.size:raise ValueError('zero sideband noise')
    floor=1e-6*np.median(positive)
    pixel_noise=np.sqrt(np.maximum(variance,floor))
    totals=np.concatenate([np.diff(left[:,aperture].sum(1)),np.diff(right[:,aperture].sum(1))])
    sigma=MAD*np.median(abs(totals-np.median(totals)))/np.sqrt(2)
    if not sigma>0:raise ValueError('zero aperture scale')
    return {'reference':np.median(cube[side],axis=0),'pixel_noise':pixel_noise,'sigma':float(sigma),'variance_floor':float(floor)}


def source_fit(reference,profile,plane,noise,support):
    design=np.column_stack([profile[support],plane[support]])/noise[support,None]
    beta,_,rank,singular=np.linalg.lstsq(design,reference[support]/noise[support],rcond=1e-10)
    condition=float(singular[0]/singular[-1]) if singular[-1]>0 else None
    valid=bool(rank==4 and condition is not None and condition<=1e8 and beta[0]>0)
    return {'beta':beta,'rank':int(rank),'condition':condition,'valid':valid}


def protected_plane(profiles,plane,noise,outside):
    source=profiles[:,outside].T/noise[outside,None]
    u,s,_=np.linalg.svd(source,full_matrices=False)
    rank=int(np.sum(s>1e-10*s[0])) if s[0]>0 else 0
    b=u[:,:rank];x=plane[outside]/noise[outside,None]
    projected=x-b@(b.T@x)
    ps=np.linalg.svd(projected,compute_uv=False)
    prank=int(np.sum(ps>1e-10*ps[0])) if ps[0]>0 else 0
    condition=float(ps[0]/ps[-1]) if ps[-1]>0 else None
    valid=bool(prank==3 and condition is not None and condition<=1e8)
    operator=np.linalg.pinv(projected,rcond=1e-10)/noise[outside][None,:] if valid else None
    return {'operator':operator,'source_rank':rank,'plane_rank':prank,'condition':condition,'valid':valid}


def sample_positions(model,pixels,source,positions_xy,shift_xy=(0.,0.)):
    displacement=np.asarray(positions_xy)+shift_xy
    if np.max(abs(displacement))>.5:raise ValueError('displacement outside frozen half-pixel domain')
    samples=[model.sample(pixels,source+p) for p in displacement]
    return np.stack([s.flux for s in samples]),np.stack([s.uncertainty_envelope for s in samples])


def corrections(delta,motion,plane,outside,operator):
    p=None if operator is None else plane@(operator@delta[outside])
    combined=None if operator is None or motion is None else motion+plane@(operator@(delta-motion)[outside])
    return {'motion':motion,'plane':p,'combined':combined}


def response_metrics(expected,actual):
    norm=float(np.dot(expected,expected))
    if not norm>0:raise ValueError('empty pulse aperture')
    return {'gain':float(np.dot(expected,actual)/norm),'relative_distortion':float(np.linalg.norm(actual-expected)/np.sqrt(norm))}
