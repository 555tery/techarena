"""Fixed exact-speed H/B/M compositions; no builds or writes."""
from pathlib import Path
import hashlib,importlib.util
PATCHES=[
('/tmp/pipes_gap_handles_round3_20261022.py','5305cccd5136d688c41da6be272b8ac4fbebb28242f95c4d197524ff3235ff83'),
('/tmp/pipes_same_gap_lookup_round3_20261022.py','2ca12c42a6fe872aa523f8f34c42c32103be3cfeb8cf68ff709b4f2aa77296f6'),
('/tmp/pipes_size_buckets_round3_20261022.py','4d8def6230cc759ea13ab22029a8e98f92283eacdbff990386bee86a67ee5be9'),
('/tmp/pipes_size_bucket_masks_round3_20261022.py','d997d024c97ece94d7d68b80b775e96529c91ff4440420db30f99a4d40cf9b65')]
def apply_cj(source,mode):
 assert mode in ['H','B','M']
 for p,pin in PATCHES[:{'H':2,'B':3,'M':4}[mode]]:
  assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==pin,p
  spec=importlib.util.spec_from_file_location('_speed_'+pin[:16],p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  source=m.apply_cj(source)
 return source
