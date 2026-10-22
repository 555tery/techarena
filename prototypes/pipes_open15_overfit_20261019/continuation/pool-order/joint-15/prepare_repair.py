# OPEN15_FULL_OVERFIT: local final/late-temporary exact repacking with fixed shared prefix.
from pathlib import Path
import json
r=Path(__file__).resolve().parent;v=Path('/Users/555tery/techarena/data/pipes/open/15.in').read_text().split();n=int(v[1]);L=[0];B=[0];D=[n]
for t,c in enumerate(map(int,v[2:n+2])):
 if c>0:L.append(c);B.append(t);D.append(n)
 else:D[-c]=t
p=[-1]+list(map(int,(r/'15-conditioned_knapsack-2002.txt').read_text().split()));H=418780;bad=[i for i in range(1,len(L)) if p[i]+L[i]>H];print('bad',[(i,L[i],B[i],D[i]) for i in bad]);assert bad==[130149]
for radius in [0,100]:
 mov=set(bad)
 for q in range(4007,len(L)):
  if max(B[q],B[130149])<min(D[q],D[130149]) or B[q]>=D[130149]:
   if 19500-radius<p[q]+L[q] and p[q]<21020+radius:mov.add(q)
  if p[q]>418700:mov.add(q)
 part=[(-1 if i in mov else p[i]) for i in range(1,len(L))];(r/f'partial-{radius}.txt').write_text('\n'.join(map(str,part))+'\n');print(radius,len(mov))
