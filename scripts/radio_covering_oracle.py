"""Independent forward derivatives of scalar orbit/time equations for tests.

Differentiate convergent Newton/fixed-point iterations, not the analytic bound
formulas. This is a small binary64 oracle, without arrays or bank generation.
"""
import math


class Dual:
    def __init__(self,value,derivative=(0.,)*6):
        self.value=float(value);self.derivative=tuple(derivative)
    @staticmethod
    def lift(x):return x if isinstance(x,Dual) else Dual(x)
    def __add__(self,other):
        o=self.lift(other);return Dual(self.value+o.value,[x+y for x,y in zip(self.derivative,o.derivative)])
    __radd__=__add__
    def __neg__(self):return Dual(-self.value,[-x for x in self.derivative])
    def __sub__(self,other):return self+-self.lift(other)
    def __rsub__(self,other):return self.lift(other)+-self
    def __mul__(self,other):
        o=self.lift(other);return Dual(self.value*o.value,[x*o.value+self.value*y for x,y in zip(self.derivative,o.derivative)])
    __rmul__=__mul__
    def __truediv__(self,other):
        o=self.lift(other);return Dual(self.value/o.value,[(x*o.value-self.value*y)/o.value**2 for x,y in zip(self.derivative,o.derivative)])
    def __rtruediv__(self,other):return self.lift(other)/self
    def __pow__(self,power):return Dual(self.value**power,[power*self.value**(power-1)*x for x in self.derivative])


def sin(x):return Dual(math.sin(x.value),[math.cos(x.value)*v for v in x.derivative])
def cos(x):return Dual(math.cos(x.value),[-math.sin(x.value)*v for v in x.derivative])


def scalar_derivatives(values,reception_seconds,reference_hz):
    if len(values)!=6:raise ValueError("six coordinates required")
    coordinates=[Dual(v,[float(i==j) for j in range(6)]) for i,v in enumerate(values)]
    P,a,projection,e,M0,omega=coordinates
    P=P*86400.;a=a*149597870700.;n=2*math.pi/P;A=a*projection;c=299792458.
    def state(t):
        M=M0+n*t;E=M
        for _ in range(16):E=E-(E-e*sin(E)-M)/(1-e*cos(E))
        x=a*(cos(E)-e);y=a*(1-e*e)**.5*sin(E)
        Edot=n/(1-e*cos(E))
        vx=-a*sin(E)*Edot;vy=a*(1-e*e)**.5*cos(E)*Edot
        z=-projection*(x*sin(omega)+y*cos(omega))
        vz=-projection*(vx*sin(omega)+vy*cos(omega))
        speed2=vx*vx+vy*vy
        return z,vz,speed2
    z0,v0,x0=state(Dual(0))
    tau=Dual(reception_seconds)
    for _ in range(16):tau=reception_seconds-(state(tau)[0]-z0)/c
    z,v,x=state(tau)
    R=(1+v0/c)/(1+v/c)
    S=R*((1-x/c**2)/(1-x0/c**2))**.5
    f=reference_hz*S
    return {"frequency_hz":f.value,"frequency_derivatives_hz_per_unit":list(f.derivative),
        "emission_seconds":tau.value,"emission_time_derivatives_seconds_per_unit":list(tau.derivative),
        "arrival_residual_seconds":(tau+(z-z0)/c-reception_seconds).value}
