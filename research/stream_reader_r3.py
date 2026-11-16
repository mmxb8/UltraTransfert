"""Research-only allocation reduction; same UTCS1 grammar and checks.

The inherited advance() keeps all block and stream digests and verifies the
terminal before the final bytes are returned. No production module is patched
except inside explicitly scoped test/benchmark contexts.
"""
from ultra.blockstream import BlockReader
from ultra.compression import CodecError

RESEARCH_VERSION = 'R3.1'


class LeanBlockReader(BlockReader):
    def exact(self, n):
        first = self.stream.read(n)
        if len(first) == n:
            return first
        if not first:
            raise CodecError('Flux de blocs tronqué')
        parts = bytearray(first)
        while len(parts) < n:
            part = self.stream.read(n-len(parts))
            if not part:
                raise CodecError('Flux de blocs tronqué')
            parts.extend(part)
        return bytes(parts)

    def read(self, n):
        if type(n) is not int or n < 0:
            raise CodecError('Lecture bornée requise')
        if n == 0:
            return b''
        chunks = []
        remaining = n
        while remaining:
            if self.position == len(self.buffer) and not self.finished:
                self.advance()
            if self.finished:
                break
            end = min(self.position+remaining, len(self.buffer))
            piece = self.buffer[self.position:end]
            if isinstance(piece, memoryview):
                piece = bytes(piece)
            self.position = end
            remaining -= len(piece)
            chunks.append(piece)
            if self.position == len(self.buffer) and self.total == self.expected:
                self.advance()
        if not chunks:
            return b''
        return chunks[0] if len(chunks) == 1 else b''.join(chunks)


def raw_view_unframe(data):
    """UTCP1 raw identity blocks only; other recipes use the R1 decoder.

    The immutable backing bytes stay alive until the block is consumed. Header,
    raw length and SHA-256 are checked before exposing any view. This function
    is ONLY installed by the scoped research harness, never in the application.
    """
    import hashlib
    from research.predictive_compression import header, unframe
    h, start = header(data)
    if (h['codec'], h['width'], h['predictor']) != ('raw',1,'none'):
        return unframe(data)
    payload = memoryview(data)[start:]
    if len(payload) != h['size']:
        raise CodecError('Taille décompressée incorrecte')
    if hashlib.sha256(payload).hexdigest() != h['sha256']:
        raise CodecError('Predictor digest mismatch')
    return payload
