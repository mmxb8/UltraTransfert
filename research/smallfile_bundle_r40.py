"""R4 research container, never advertised as a production transport.

At most 4 MiB per group, 256 files per group and 64 MiB / 4096 entries
per experiment. Rehydration uses the unchanged Transfer engine. No extraction
paths are opened by this parser. Input is an immutable bounded snapshot.
"""
from dataclasses import asdict, replace
import hashlib
import io
import json
import lzma
from pathlib import Path
import struct

from ultra.compression import CodecError, ZSTD
from ultra.engine import (Entry, LocalSource, TransferError, install_no_replace,
                          validate_entries)

MAGIC = b'UTSB1'
MAX_GROUP = 4*1024*1024
MAX_TOTAL = 64*1024*1024
MAX_ENTRIES = 4096
MAX_MANIFEST = 2*1024*1024
MAX_FILE = 64*1024
HEADER = struct.Struct('!BII32s')
CODECS = {'raw': 0, 'zstd1': 1, 'zstd3': 2, 'lzma1': 3, 'auto': 4}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CodecError('Duplicate manifest key')
        result[key] = value
    return result


def _exact(stream, size):
    data = bytearray()
    while len(data) < size:
        part = stream.read(size-len(data))
        if not part:
            raise CodecError('Truncated bundle')
        data.extend(part)
    return bytes(data)


def _compress(data, codec):
    if codec == 'raw':
        return 0, data
    if codec == 'lzma1':
        return 3, lzma.compress(data, preset=1)
    if codec not in ('zstd1', 'zstd3', 'auto') or ZSTD is None:
        raise CodecError('Codec unavailable')
    payload = ZSTD.compress(data, 3 if codec == 'zstd3' else 1)
    if codec == 'auto' and len(payload) >= len(data):
        return 0, data
    return (2 if codec == 'zstd3' else 1), payload


def _decode(kind, data, size):
    if kind == 0:
        result = data
    elif kind in (1, 2) and ZSTD:
        result = ZSTD.decompress(data, size)
    elif kind == 3:
        decoder = lzma.LZMADecompressor(memlimit=64*1024*1024)
        result = decoder.decompress(data, max_length=size+1)
        if not decoder.eof or decoder.unused_data:
            raise CodecError('Invalid or excessive LZMA stream')
    else:
        raise CodecError('Unknown codec')
    if len(result) != size:
        raise CodecError('Invalid decoded size')
    return result


def pack(root, output, *, codec='auto', group_bytes=MAX_GROUP, group_files=256):
    """Create one bounded experiment snapshot; existing outputs are never replaced."""
    if codec not in CODECS or type(group_bytes) is not int or not 1 <= group_bytes <= MAX_GROUP:
        raise ValueError('Invalid codec/group size')
    if type(group_files) is not int or not 1 <= group_files <= 256:
        raise ValueError('Invalid file count')
    output = Path(output).absolute()
    source = LocalSource(root)
    if source.root == output or source.root in output.parents:
        raise TransferError('Bundle output must be outside the source')
    if len(source.entries) > MAX_ENTRIES or sum(e.size for e in source.entries) > MAX_TOTAL:
        raise CodecError('Experiment exceeds total bounds')
    groups, entries, data = [], [], bytearray()
    count = 0
    for e in source.entries:
        if e.kind == 'dir':
            entries.append(replace(e, identity=()))
            continue
        if e.size > min(MAX_FILE, group_bytes):
            raise CodecError('Not a small file')
        if count and (len(data)+e.size > group_bytes or count == group_files):
            groups.append(bytes(data)); data.clear(); count = 0
        with source.open(e) as stream:
            content = stream.read(e.size+1)
        source.check(e)
        if len(content) != e.size:
            raise TransferError('Source changed during packing')
        entries.append(replace(e, identity=(), sha256=hashlib.sha256(content).hexdigest()))
        data.extend(content); count += 1
    if count:
        groups.append(bytes(data))
    source.check_all()
    manifest = json.dumps({'entries': [asdict(e) for e in entries],
                           'groups': [len(g) for g in groups]},
                          ensure_ascii=False, separators=(',', ':')).encode()
    if len(manifest) > MAX_MANIFEST:
        raise CodecError('Manifest too large')
    # Exclusive private staging; rename_no_replace is the normal engine primitive.
    temporary = output.with_name(output.name+'.part')
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            stream.write(MAGIC+struct.pack('!I', len(manifest))+manifest)
            for group in groups:
                kind, payload = _compress(group, codec)
                stream.write(HEADER.pack(kind, len(group), len(payload), hashlib.sha256(group).digest()))
                stream.write(payload)
            import os
            stream.flush(); os.fsync(stream.fileno())
        source.check_all()
        install_no_replace(temporary, output)
    finally:
        if created:
            temporary.unlink(missing_ok=True)
    return {'groups': len(groups), 'files': sum(e.kind == 'file' for e in entries),
            'input_bytes': sum(len(g) for g in groups), 'container_bytes': output.stat().st_size}


class BundleSource:
    """Parse/verify bounded snapshot in memory, then expose ordinary source API.

64 MiB total bound is deliberate. Future production work must stream groups
and negotiate an authenticated inventory; this object is research-only.
"""
    def __init__(self, path):
        with open(path, 'rb') as stream:
            if _exact(stream, len(MAGIC)) != MAGIC:
                raise CodecError('Unknown bundle')
            size = struct.unpack('!I', _exact(stream, 4))[0]
            if size > MAX_MANIFEST:
                raise CodecError('Excessive manifest')
            manifest_bytes = _exact(stream, size)
            manifest = json.loads(manifest_bytes, object_pairs_hook=_unique)
            if not isinstance(manifest, dict) or set(manifest) != {'entries', 'groups'}:
                raise CodecError('Invalid manifest')
            if not isinstance(manifest['entries'], list) or len(manifest['entries']) > MAX_ENTRIES:
                raise CodecError('Excessive entries')
            self.entries = []
            for record in manifest['entries']:
                if not isinstance(record, dict) or set(record) != {'path','kind','size','mtime_ns','mode','identity','sha256'}:
                    raise CodecError('Invalid entry record')
                if (not isinstance(record['path'], str) or not isinstance(record['kind'], str)
                        or any(type(record[k]) is not int for k in ('size','mtime_ns','mode'))
                        or record['identity'] != [] or not 0 <= record['mode'] <= 0o7777
                        or record['size'] > MAX_FILE):
                    raise CodecError('Invalid entry')
                if record['kind'] == 'file' and not isinstance(record['sha256'], str):
                    raise CodecError('Missing digest')
                if record['kind'] == 'dir' and (record['size'] or record['sha256'] is not None):
                    raise CodecError('Invalid directory')
                self.entries.append(Entry(**{**record, 'identity': ()}))
            validate_entries(self.entries)
            sizes = manifest['groups']
            if (not isinstance(sizes, list) or len(sizes) > MAX_ENTRIES
                    or any(type(n) is not int or not 0 <= n <= MAX_GROUP for n in sizes)
                    or sum(sizes) > MAX_TOTAL
                    or sum(sizes) != sum(e.size for e in self.entries)):
                raise CodecError('Invalid group bounds')
            contents = bytearray()
            for size in sizes:
                kind, raw_size, encoded_size, sha = HEADER.unpack(_exact(stream, HEADER.size))
                if raw_size != size or encoded_size > MAX_GROUP+65536:
                    raise CodecError('Invalid group sizes')
                data = _decode(kind, _exact(stream, encoded_size), raw_size)
                if hashlib.sha256(data).digest() != sha:
                    raise CodecError('Corrupt group')
                contents.extend(data)
            if stream.read(1):
                raise CodecError('Trailing data')
        self._files = {}
        offset = 0
        for e in self.entries:
            if e.kind == 'file':
                data = bytes(contents[offset:offset+e.size]); offset += e.size
                if hashlib.sha256(data).hexdigest() != e.sha256:
                    raise CodecError('Corrupt file')
                self._files[e.path] = data
        # Content-based identity for this snapshot only; NOT a signed cross-transport ID.
        self.identity = 'research-bundle:' + hashlib.sha256(manifest_bytes).hexdigest()

    def open(self, entry, offset=0):
        self.check(entry)
        stream = io.BytesIO(self._files[entry.path]); stream.seek(offset)
        return stream

    def check(self, entry):
        if entry not in self.entries or entry.kind != 'file':
            raise TransferError('Unknown bundle entry')

    def check_all(self, cancel=None):
        from ultra.engine import check_cancel
        check_cancel(cancel)  # No mutable filesystem source after snapshot verification.
