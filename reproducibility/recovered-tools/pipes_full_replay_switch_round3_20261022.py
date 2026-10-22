"""One fixed switch: current boundary-index guard5 -> full replay guard0."""
import hashlib
PARENT_SHA='f1f6240fb7ca7e099408a02bb2aeb9926f4240425afbd7be4eebd25ee6a2ac4a'
OLD='                (command < 0 || (actual.fits(address, command) && causalReplayAllowed(actual, address, command)))'
NEW='                (command < 0 || actual.fits(address, command))'
def apply_cj(source):
 assert hashlib.sha256(source.encode()).hexdigest()==PARENT_SHA
 assert source.count(OLD)==1
 return source.replace(OLD,NEW)
