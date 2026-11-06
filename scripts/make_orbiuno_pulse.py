#!/usr/bin/env python3
"""Regeneración determinista de ORBIUNO PULSE Propuesta 3 aprobada."""
import sys
import numpy as np, scipy.signal as sig, soundfile as sf
from pathlib import Path
SR=32000; DUR=24.; N=int(SR*DUR)
rng=np.random.default_rng(1406)
a=np.zeros(N,dtype=np.float64)
BPM=112.; beat=60/BPM
def add(t,s,scale=1):
    i=int(t*SR)
    if i>=N:return
    l=min(len(s),N-i)
    if l>0:a[i:i+l]+=s[:l]*scale
def midi(m):return 440*2**((m-69)/12)
def env(l,atk=.01,dec=.1,sustain=.4,rel=.2):
    tt=np.arange(l)/SR;out=np.minimum(1,tt/max(atk,.001))
    if dec:out*=sustain+(1-sustain)*np.exp(-tt/max(dec,.001))
    if rel:out*=np.minimum(1,(tt[-1]-tt)/rel)
    return np.maximum(out,0)
def synth(m,dur,kind='bell'):
    n=int(SR*dur);t=np.arange(n)/SR;f=midi(m)
    if kind=='bell':
        s=np.sin(2*np.pi*f*t)+.30*np.sin(2*np.pi*2.01*f*t)+.10*np.sin(2*np.pi*3.98*f*t);e=env(n,.008,.26,.13,.18)
    elif kind=='pad':
        s=np.sin(2*np.pi*f*t)+.13*np.sin(2*np.pi*2*f*t)+.10*np.sin(2*np.pi*f*1.002*t);e=env(n,.31,.3,.66,.65)
    elif kind=='bass':
        s=np.sin(2*np.pi*f*t)+.20*np.sin(2*np.pi*2*f*t);e=env(n,.014,.19,.18,.22)
    else:
        s=np.sin(2*np.pi*f*t)+.18*np.sin(2*np.pi*2*f*t);e=env(n,.018,.26,.3,.19)
    return e*s
def kick():
    d=.36;n=int(d*SR);t=np.arange(n)/SR;phase=2*np.pi*(78*t+60*(1-np.exp(-t*35))/35)
    return np.sin(phase)*np.exp(-t*19)+.12*rng.standard_normal(n)*np.exp(-t*70)
def snare():
    d=.24;n=int(d*SR);t=np.arange(n)/SR
    hp=sig.sosfilt(sig.butter(2,900,fs=SR,output='sos',btype='highpass'),rng.standard_normal(n))
    return .5*hp*np.exp(-t*20)+.14*np.sin(2*np.pi*190*t)*np.exp(-t*29)
def hat():
    d=.10;n=int(d*SR);t=np.arange(n)/SR
    s=sig.sosfilt(sig.butter(2,4500,fs=SR,output='sos',btype='highpass'),rng.standard_normal(n))
    return s*np.exp(-t*49)
for at,m in [(0.04,67),(.37,71),(.68,74),(.94,79),(1.31,76),(1.58,74),(1.86,79)]:add(at,synth(m,.7),.12)
rlen=int(1.45*SR);t=np.arange(rlen)/SR
noise=rng.standard_normal(rlen)
filter_noise=sig.sosfilt(sig.butter(2,1500,fs=SR,btype='highpass',output='sos'),noise)
add(1.42,filter_noise*(t/1.45)**2*np.sin(np.pi*t/1.45)**.22,.035)
add(2.92,kick(),.36);add(2.92,synth(79,1.1,'bell'),.16);add(2.92,synth(67,1.8,'pad'),.13)
chords=[[55,59,62,67],[57,60,64,69],[60,64,67,72],[62,66,69,74]]
for j,start in enumerate(np.arange(3.15,DUR,4*beat)):
    chord=chords[(j//2)%len(chords)]
    for m in chord:add(start,synth(m,4*beat+.28,'pad'),.025)
    for k in range(4):
        ts=start+k*beat;add(ts,kick(),.108 if k in [0,2] else .067)
        if k in (1,3):add(ts,snare(),.025)
        add(ts+beat/2,hat(),.014);add(ts,hat(),.008);add(ts,synth(chord[0]-12,.32,'bass'),.062)
    if j%2==0:add(start+3.1*beat,synth(chord[2]+12,.4,'bell'),.025)
for at,m in [(21.0,74),(21.28,79),(21.55,83),(21.84,79)]:add(at,synth(m,.8),.045)
fadein=np.minimum(1,np.arange(N)/(.015*SR));fadeout=np.minimum(1,(N-np.arange(N))/(.5*SR))
a*=fadein*fadeout
peak=np.max(np.abs(a));a=np.tanh(a*.86/max(peak,.001))*0.62
p=Path(sys.argv[1] if len(sys.argv)>1 else 'ORBIUNO_Pulse.wav');p.parent.mkdir(parents=True,exist_ok=True);sf.write(p,a,SR)
print(p,'peak',float(np.max(np.abs(a))))
