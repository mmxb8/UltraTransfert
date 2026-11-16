"""Trusted-fixture tar/ZIP references for the R4 benchmark, not a product importer."""
import hashlib
import io
import os
from pathlib import Path
import tarfile
import zipfile
from research.smallfile_bundle import _compress, _decode
from ultra.engine import LocalSource, digest, inventory


def pack_archive(source, output, method):
    src=LocalSource(source);expected={};raw=io.BytesIO()
    if method=='zip-deflate':
        with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
            for e in src.entries:
                if e.kind=='dir': archive.writestr(e.path+'/',b'')
                else:
                    with src.open(e) as stream: data=stream.read(e.size+1)
                    src.check(e)
                    if len(data)!=e.size: raise RuntimeError('Source changed')
                    expected[e.path]=hashlib.sha256(data).hexdigest()
                    archive.writestr(e.path,data)
        kind=0;payload=raw.getvalue()
    else:
        with tarfile.open(fileobj=raw,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for e in src.entries:
                info=tarfile.TarInfo(e.path);info.mode=e.mode;info.mtime=e.mtime_ns/1e9
                if e.kind=='dir': info.type=tarfile.DIRTYPE;archive.addfile(info)
                else:
                    with src.open(e) as stream: data=stream.read(e.size+1)
                    src.check(e)
                    if len(data)!=e.size: raise RuntimeError('Source changed')
                    expected[e.path]=hashlib.sha256(data).hexdigest()
                    info.size=len(data);archive.addfile(info,io.BytesIO(data))
        kind,payload=_compress(raw.getvalue(),method.split('-')[1])
    src.check_all()
    with open(output,'xb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())
    return dict(kind=kind,raw_size=len(raw.getbuffer()),expected=expected,
                inventory=[(e.path,e.kind,e.size) for e in src.entries])


def restore_archive(path,destination,method,metadata):
    destination=Path(destination);destination.mkdir()  # Never use an existing directory.
    payload=Path(path).read_bytes()
    data=_decode(metadata['kind'],payload,metadata['raw_size'])
    # These archives come only from our own checked fixtures + verified TLS file.
    # This helper deliberately is NOT a general untrusted archive importer.
    if method=='zip-deflate':
        with zipfile.ZipFile(io.BytesIO(data)) as archive: archive.extractall(destination)
    else:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
            archive.extractall(destination,filter='data')
    actual=inventory(destination)
    if [(e.path,e.kind,e.size) for e in actual]!=metadata['inventory']:
        raise RuntimeError('Archive inventory mismatch')
    for e in actual:
        if e.kind=='file':
            with open(destination/e.path,'rb') as stream: os.fsync(stream.fileno())
            if digest(destination/e.path)!=metadata['expected'][e.path]:
                raise RuntimeError('Archive output digest mismatch')
