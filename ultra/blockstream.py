"""Flux expérimental UTCS1 : blocs UTCL1 bornés et fin explicite vérifiée."""
import hashlib
import struct

from .compression import AdaptiveEncoder, CodecError, MAX_BLOCK, MAX_FRAME, unframe

ENCODING = 'x-ultra-blocks-v1'
MAGIC = b'UTCS1'


def write_stream(source, output, length, encoder=None, on_block=None):
    encoder = encoder or AdaptiveEncoder()
    remaining = length
    full = hashlib.sha256()
    wire_bytes = 0

    def emit(data):
        nonlocal wire_bytes
        output.write(data)
        wire_bytes += len(data)

    emit(MAGIC)
    while remaining:
        data = source.read(min(MAX_BLOCK, remaining))
        if not data:
            raise CodecError('Source tronquée')
        encoded = encoder.encode(data)
        emit(struct.pack('!I', len(encoded)))
        emit(encoded)
        full.update(data)
        remaining -= len(data)
        if on_block:
            on_block(len(data))
    emit(struct.pack('!IQ', 0, length) + full.digest())
    return wire_bytes


class BlockReader:
    """Un bloc décodé plus le tampon demandé, longueur totale obligatoire."""
    def __init__(self, stream, expected_length, *, decoder=None):
        if type(expected_length) is not int or expected_length < 0:
            raise CodecError('Longueur attendue invalide')
        self.decoder = decoder
        self.stream = stream
        self.expected = expected_length
        self.total = 0
        self.buffer = b''
        self.position = 0
        self.full = hashlib.sha256()
        self.started = False
        self.finished = False

    def exact(self, n):
        parts = bytearray()
        while len(parts) < n:
            part = self.stream.read(n-len(parts))
            if not part:
                raise CodecError('Flux de blocs tronqué')
            parts.extend(part)
        return bytes(parts)

    def advance(self):
        if not self.started:
            if self.exact(len(MAGIC)) != MAGIC:
                raise CodecError('Version de flux inconnue')
            self.started = True
        length = struct.unpack('!I', self.exact(4))[0]
        if length == 0:
            total = struct.unpack('!Q', self.exact(8))[0]
            sha = self.exact(32)
            if total != self.total or total != self.expected or sha != self.full.digest():
                raise CodecError('Bilan du flux incorrect')
            if self.stream.read(1):
                raise CodecError('Données après la fin du flux')
            self.finished = True
            self.buffer = b''
            self.position = 0
            return
        if length > MAX_FRAME:
            raise CodecError('Trame trop volumineuse')
        data = (self.decoder or unframe)(self.exact(length))
        if not data or self.total+len(data) > self.expected:
            raise CodecError('Bloc vide ou longueur excessive')
        self.total += len(data)
        self.full.update(data)
        self.buffer = data
        self.position = 0

    def read(self, n):
        if type(n) is not int or n < 0:
            raise CodecError('Lecture bornée requise')
        if n == 0:
            return b''
        parts = bytearray()
        while len(parts) < n:
            if self.position == len(self.buffer) and not self.finished:
                self.advance()
            if self.finished:
                break
            end = min(self.position+n-len(parts), len(self.buffer))
            parts.extend(self.buffer[self.position:end])
            self.position = end
            # Vérifier le terminal avant de livrer les derniers octets.
            if self.position == len(self.buffer) and self.total == self.expected:
                self.advance()
        return bytes(parts)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)

    def close(self):
        self.stream.close()
