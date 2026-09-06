"""Explicit local dataset facade: source persistence tests, never HDF5 decoding."""
import numpy as np


def fixture_values(row,start,stop):
    channels=np.arange(start,stop,dtype=np.int64)
    return (((channels*1103515245+(row+1)*12345)%104729).astype('<f4')/np.float32(1024))


class FixtureDataset:
    def __init__(self,definition,fail_after=None):
        self.shape=tuple(definition['expected_header']['dataset_shape'])
        self.dtype=np.dtype('<f4');self.chunks=(1,1,4096);self.attrs={}
        self.requests=[];self.fail_after=fail_after
    def __getitem__(self,key):
        if self.fail_after is not None and len(self.requests)>=self.fail_after:
            raise InterruptedError('intentional fixture interruption')
        row,beam,channels=key
        if beam!=0 or channels.step is not None:raise ValueError('wrong hyperslab')
        self.requests.append((row,beam,channels.start,channels.stop))
        return fixture_values(row,channels.start,channels.stop)


class FixtureHandle:
    def __init__(self,definition,fail_after=None):
        h=definition['expected_header']
        self.attrs={'source_name':h['source_name'],'src_raj':h['src_raj_hours'],
            'src_dej':h['src_dej_deg'],'tstart':h['tstart_mjd'],'tsamp':h['tsamp_s'],
            'fch1':h['fch1_mhz'],'foff':h['foff_mhz']}
        self.dataset=FixtureDataset(definition,fail_after)
    def __getitem__(self,key):
        if key!='data':raise KeyError(key)
        return self.dataset
