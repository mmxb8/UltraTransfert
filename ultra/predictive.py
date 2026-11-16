"""Optional lossless predictor recipes, negotiated as x-ultra-predictive-v1.

Only a fixed grammar is decoded. No generated code, dictionaries or executable
recipes. Integer differencing includes borrows across words and is therefore
not ordinary per-word modular delta. Its modular inverse is exact. Existing
predictor/shuffle/entropy coding ideas are not claimed as new.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import time
import zlib

from .compression import (MAX_BLOCK, MAX_FRAME, CodecError, ZSTD,
                               compress, decompress, shuffle)

MAGIC = b'UTCP1'
WIDTHS = (1, 2, 4, 8, 16)
PREDICTORS = ('none', 'xor', 'subtract')


def predict(data, width, kind, inverse=False, *, inversion='division'):
    """Portable bounded-byte transform, preserving an unaligned tail verbatim.

    X is the complete little-endian aligned prefix, B=2**(8*width),
    M=2**(8*prefix_length). D=X*(1-B) mod M. Since M=B**k,
    M=1 mod (B-1); thus X=((D mod (B-1))*M-D)//(B-1) mod M.
    Division avoids the O(log k) whole-block passes of prefix doubling.
    """
    if type(width) is not int or width not in WIDTHS or kind not in PREDICTORS:
        raise CodecError('Invalid predictor recipe')
    if len(data) > MAX_BLOCK:
        raise CodecError('Predictor block too large')
    if kind == 'none' or not data:
        return data
    length = len(data)//width*width
    if not length:
        return data
    bits, shift = length*8, width*8
    mask = (1 << bits)-1
    x = int.from_bytes(data[:length], 'little')
    if not inverse:
        x = (x ^ (x << shift)) & mask if kind == 'xor' else (x-(x << shift)) & mask
    elif kind == 'subtract' and inversion == 'division':
        divisor = (1 << shift)-1
        x = (((x % divisor) << bits)-x)//divisor & mask
    else:
        while shift < bits:
            x = (x ^ (x << shift)) & mask if kind == 'xor' else (x+(x << shift)) & mask
            shift *= 2
    return x.to_bytes(length, 'little')+data[length:]


def _prefix(data, recipe, sha256=None):
    codec, width, predictor = recipe
    h = json.dumps({'size':len(data), 'codec':codec, 'width':width,
                    'predictor':predictor,
                    'sha256':hashlib.sha256(data).hexdigest() if sha256 is None else sha256},
                   sort_keys=True, separators=(',', ':')).encode()
    return MAGIC+struct.pack('!I',len(h))+h


def frame(data, recipe=('raw', 1, 'none'), *, fallback=True):
    if len(data) > MAX_BLOCK:
        raise CodecError('Predictor block too large')
    codec, width, predictor = recipe
    if codec not in ('raw', 'zlib1', 'zstd1', 'zstd3'):
        raise CodecError('Invalid codec')
    transformed = shuffle(predict(data, width, predictor), width)
    payload = compress(transformed, codec)
    # Hash the original bytes once, including when a recipe expands and falls
    # back to raw. Compare complete frame sizes before joining a large payload.
    sha256 = hashlib.sha256(data).hexdigest()
    prefix = _prefix(data, recipe, sha256)
    if fallback and recipe != ('raw', 1, 'none'):
        raw_prefix = _prefix(data, ('raw', 1, 'none'), sha256)
        if len(prefix)+len(payload) > len(raw_prefix)+len(data):
            return raw_prefix+data
    return prefix+payload


def header(data):
    if not isinstance(data, bytes) or len(data) < 9 or data[:5] != MAGIC or len(data) > MAX_FRAME:
        raise CodecError('Invalid predictor frame')
    length = struct.unpack('!I', data[5:9])[0]
    if not 1 <= length <= 4096 or 9+length > len(data):
        raise CodecError('Invalid predictor header length')
    try:
        def unique_pairs(pairs):
            h = {}
            for key, value in pairs:
                if key in h:
                    raise CodecError('Duplicate predictor header key')
                h[key] = value
            return h
        h = json.loads(data[9:9+length], object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise CodecError('Invalid predictor header') from exc
    if not isinstance(h, dict) or set(h) != {'size', 'codec', 'width', 'predictor', 'sha256'}:
        raise CodecError('Invalid predictor fields')
    if type(h['size']) is not int or not 0 <= h['size'] <= MAX_BLOCK:
        raise CodecError('Invalid predictor size')
    if type(h['width']) is not int or h['width'] not in WIDTHS:
        raise CodecError('Invalid predictor width')
    if h['predictor'] not in PREDICTORS or h['codec'] not in ('raw', 'zlib1', 'zstd1', 'zstd3'):
        raise CodecError('Unknown predictor or codec')
    sha = h['sha256']
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
        raise CodecError('Invalid predictor digest')
    return h, 9+length


def unframe(data):
    h, start = header(data)
    try:
        restored = shuffle(decompress(data[start:],h['codec'],h['size']), h['width'], True)
    except zlib.error as exc:
        raise CodecError('Invalid compressed predictor payload') from exc
    restored = predict(restored, h['width'], h['predictor'], True)
    if hashlib.sha256(restored).hexdigest() != h['sha256']:
        raise CodecError('Predictor digest mismatch')
    return restored


def _sample(data, unit=4096):
    if len(data) <= 3*unit:
        return data
    offsets = (0, (len(data)//2//16)*16, ((len(data)-unit)//16)*16)
    return b''.join(data[o:o+unit] for o in offsets)


class PredictiveEncoder:
    """Research encoder: bounded search, raw probe exit, recipe reuse.

    Receiver costs are measured on the sender. Fast and slow endpoints still
    require separate validation. Every emitted block remains independently
    framed, hashed and reversible; there is no stateful dictionary dependency.
    """
    def __init__(self, megabits_per_second=100, allowed_codecs=None, retune_every=16, **unused):
        if not math.isfinite(megabits_per_second) or megabits_per_second <= 0:
            raise CodecError('Positive finite bandwidth required')
        if type(retune_every) is not int or retune_every < 1:
            raise CodecError('Invalid tuning interval')
        self.rate = megabits_per_second*1e6/8
        available = ['raw', 'zstd1', 'zstd3'] if ZSTD else ['raw', 'zlib1']
        self.allowed = available if allowed_codecs is None else [c for c in available if c in allowed_codecs]
        if 'raw' not in self.allowed:
            raise CodecError('Raw codec required')
        self.interval = retune_every
        self.recipe = None
        self.blocks = self.searches = self.reused = 0
        self.last_search = []

    def _select(self, data):
        sample = _sample(data,16384)
        raw = ('raw', 1, 'none')
        self.last_search = []
        fast = 'zstd1' if 'zstd1' in self.allowed else 'zlib1'
        if fast not in self.allowed or len(data) < 1024:
            return raw
        # Three probes terminate early on already compressed/noise-like input.
        if all(len(compress(shuffle(sample,w), fast)) >= len(sample)*.99 for w in (1,4,8)):
            return raw
        candidates = [raw]
        for codec in self.allowed:
            if codec != 'raw':
                candidates.extend((codec,w,'none') for w in (1,2,4,8))
        scale = len(data)/max(1,len(sample))
        def evaluate(recipe):
            codec,width,predictor = recipe
            started = time.perf_counter()
            encoded = compress(shuffle(predict(sample,width,predictor),width),codec)
            enc = time.perf_counter()-started
            started = time.perf_counter()
            restored = predict(shuffle(decompress(encoded,codec,len(sample)),width,True),width,predictor,True)
            dec = time.perf_counter()-started
            if restored != sample:
                raise CodecError('Non-reversible sampled recipe')
            # Hashing and framing are common to candidates, paid on the full block.
            # Frame overhead is constant, not multiplied by sample expansion.
            cost = (enc+dec+len(encoded)/self.rate)*scale
            self.last_search.append({'recipe':recipe,'estimated_seconds':cost,
                                     'sample_encoded_bytes':len(encoded),
                                     'sample_codec_seconds':enc+dec})
        for recipe in candidates:
            evaluate(recipe)
        best=min(self.last_search,key=lambda r:r['estimated_seconds'])
        # Empirical structural gate: text/executable-like inputs and already tiny
        # payloads do not pay for arithmetic predictors. This can miss a useful
        # recipe; it is a speed heuristic, not a proof of incompressibility.
        ratio=best['sample_encoded_bytes']/max(1,len(sample))
        if best['recipe'][1] != 1 and ratio > .02:
            widths=sorted({4,8,best['recipe'][1]})
            for codec in self.allowed:
                if codec != 'raw':
                    for width in widths:
                        for predictor in ('xor','subtract'):
                            evaluate((codec,width,predictor))
        return min(self.last_search,key=lambda r:r['estimated_seconds'])['recipe']

    def encode(self, data):
        if len(data) > MAX_BLOCK:
            raise CodecError('Predictor block too large')
        retune = self.recipe is None or self.blocks % self.interval == 0
        if not retune and len(data) >= 4096:
            sample = _sample(data)
            fast = 'zstd1' if 'zstd1' in self.allowed else 'zlib1'
            if self.recipe == ('raw',1,'none') and fast in self.allowed:
                retune = any(len(compress(shuffle(sample,w),fast)) < len(sample)*.90 for w in (1,4,8))
            elif self.recipe[0] != 'raw':
                probe = frame(sample,self.recipe,fallback=False)
                if len(probe) >= len(frame(sample))*.98:
                    self.recipe = ('raw',1,'none')
        if retune:
            self.recipe = self._select(data)
            self.searches += 1
        else:
            self.reused += 1
        encoded = frame(data,self.recipe)
        h, _ = header(encoded)
        self.recipe = (h['codec'],h['width'],h['predictor'])
        self.blocks += 1
        return encoded
