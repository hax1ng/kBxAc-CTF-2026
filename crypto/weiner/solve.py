from math import isqrt
from pathlib import Path
import re
s=Path('extracted/chall.txt').read_text()
n,e,c=map(int,re.findall(r'= (\d+)',s))

def cf(a,b):
    while b:
        q,a,b=a//b,b,a%b
        yield q

# convergents of e/n
p_nm2,p_nm1=0,1
q_nm2,q_nm1=1,0
for i,a in enumerate(cf(e,n)):
    k=a*p_nm1+p_nm2
    d=a*q_nm1+q_nm2
    p_nm2,p_nm1=p_nm1,k
    q_nm2,q_nm1=q_nm1,d
    if not k or (e*d-1)%k: continue
    phi=(e*d-1)//k
    S=n-phi+1
    disc=S*S-4*n
    if disc>=0:
        t=isqrt(disc)
        if t*t==disc and (S+t)%2==0:
            p=(S+t)//2;q=(S-t)//2
            if p*q==n:
                m=pow(c,d,n)
                print('conv',i)
                print('d =',d)
                print('p =',p)
                print('q =',q)
                print('m =',m)
                b=m.to_bytes((m.bit_length()+7)//8,'big')
                print('plaintext bytes =',b)
                try: print('plaintext =',b.decode())
                except: pass
                break
else: print('not found')
