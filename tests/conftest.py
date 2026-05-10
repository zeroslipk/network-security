"""
Lower PBKDF2 iterations for tests so they run quickly.
Production paths use hashlib.pbkdf2_hmac, which is fast — but
1000 iterations still keeps tests <1s while exercising real code.
"""

import src.keymgmt.keystore as _ks
import src.auth.password_auth as _pa

_ks._ITERATIONS = 1000
_pa._ITERATIONS = 1000
