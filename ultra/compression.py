"""Compression expérimentale bornée, sans perte ; aucun codec inédit revendiqué."""
from __future__ import annotations

import ctypes as C
import ctypes.util
import hashlib
import json
import math
import struct
import time
import zlib

MAGIC = b'UTCL1'
MAX_BLOCK = 4*1024*1024
MAX_FRAME = MAX_BLOCK+65536


class CodecError(ValueError):
    pass


class Zstd:
    def __init__(self):
        name = ctypes.util.find_library('zstd')
        if not name:
            raise OSError('Bibliothèque Zstandard système absente')
        self.lib = C.CDLL(name)
        for fn, args in {
            'ZSTD_compressBound': [C.c_size_t],
            'ZSTD_compress': [C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_int],
            'ZSTD_decompress': [C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t],
            'ZSTD_findFrameCompressedSize': [C.c_void_p,C.c_size_t],
            'ZSTD_isError': [C.c_size_t],
        }.items():
            getattr(self.lib,fn).argtypes=args
            getattr(self.lib,fn).restype=C.c_uint if fn=='ZSTD_isError' else C.c_size_t
        self.lib.ZSTD_versionString.restype=C.c_char_p
        self.version=self.lib.ZSTD_versionString().decode()

    def checked(self, code):
        if self.lib.ZSTD_isError(code):
            raise CodecError('Erreur Zstandard')
        return code

    def compress(self, data, level):
        out=C.create_string_buffer(self.lib.ZSTD_compressBound(len(data)))
        n=self.checked(self.lib.ZSTD_compress(out,len(out),data,len(data),level))
        return out.raw[:n]

    def decompress(self, data, size):
        if self.checked(self.lib.ZSTD_findFrameCompressedSize(data,len(data)))!=len(data):
            raise CodecError('Données après la trame Zstandard')
        out=C.create_string_buffer(max(1,size))
        n=self.checked(self.lib.ZSTD_decompress(out,size,data,len(data)))
        if n!=size:
            raise CodecError('Longueur Zstandard incorrecte')
        return out.raw[:n]


try:
    ZSTD=Zstd()
except (OSError,AttributeError):
    ZSTD=None


def shuffle(data, width, inverse=False):
    if width not in (1,2,4,8,16):
        raise CodecError('Largeur inconnue')
    if width==1:
        return data
    count=len(data)//width
    length=count*width
    out=bytearray(len(data))
    if inverse:
        for lane in range(width):
            out[lane:length:width]=data[lane*count:(lane+1)*count]
    else:
        for lane in range(width):
            out[lane*count:(lane+1)*count]=data[lane:length:width]
    out[length:]=data[length:]
    return bytes(out)


def codecs():
    return ['raw','zlib1']+(['zstd1','zstd3'] if ZSTD else [])


def compress(data, codec):
    if codec=='raw': return data
    if codec=='zlib1': return zlib.compress(data,1)
    if codec in ('zstd1','zstd3') and ZSTD:
        return ZSTD.compress(data,int(codec[-1]))
    raise CodecError('Codec indisponible ou inconnu')


def decompress(payload, codec, size):
    if codec=='raw':
        data=payload
    elif codec=='zlib1':
        decoder=zlib.decompressobj()
        data=decoder.decompress(payload,size+1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise CodecError('Trame zlib incomplète ou excessive')
    elif codec in ('zstd1','zstd3') and ZSTD:
        data=ZSTD.decompress(payload,size)
    else:
        raise CodecError('Codec indisponible ou inconnu')
    if len(data)!=size:
        raise CodecError('Taille décompressée incorrecte')
    return data


def _frame_prefix(size, codec, width, sha256):
    header=json.dumps({'size':size,'codec':codec,'width':width,
                       'sha256':sha256},sort_keys=True,separators=(',',':')).encode()
    return MAGIC+struct.pack('!I',len(header))+header


def _encode_frame(data, codec, width, limit_expansion=False):
    if len(data)>MAX_BLOCK:
        raise CodecError('Bloc trop grand pour le laboratoire')
    payload=compress(shuffle(data,width),codec)
    sha=hashlib.sha256(data).hexdigest()
    prefix=_frame_prefix(len(data),codec,width,sha)
    if limit_expansion and codec!='raw':
        # Comparer les tailles sans allouer/hacher une deuxième trame entière.
        # La trame finalement émise porte toujours le SHA-256 du bloc source.
        raw_prefix=_frame_prefix(len(data),'raw',1,sha)
        if len(prefix)+len(payload)>len(raw_prefix)+len(data):
            return raw_prefix+data, True
    return prefix+payload, False


def frame(data, codec='raw', width=1):
    return _encode_frame(data,codec,width)[0]


def unframe(data):
    if len(data)<len(MAGIC)+4 or data[:len(MAGIC)]!=MAGIC:
        raise CodecError('Trame inconnue ou tronquée')
    start=len(MAGIC)+4
    length=struct.unpack('!I',data[len(MAGIC):start])[0]
    if not 1<=length<=4096 or len(data)<start+length or len(data)>MAX_BLOCK+65536:
        raise CodecError('Longueur de trame invalide')
    try:
        h=json.loads(data[start:start+length])
        if not isinstance(h,dict) or set(h)!={'size','codec','width','sha256'}:
            raise CodecError('Champs du manifeste invalides')
        size,width,sha=h['size'],h['width'],h['sha256']
        if type(size) is not int or not 0<=size<=MAX_BLOCK:
            raise CodecError('Taille de bloc invalide')
        if type(width) is not int or width not in (1,2,4,8,16):
            raise CodecError('Largeur invalide')
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
            raise CodecError('Empreinte invalide')
        decoded=decompress(data[start+length:],h['codec'],size)
        original=shuffle(decoded,width,True)
        if hashlib.sha256(original).hexdigest()!=sha:
            raise CodecError('Empreinte finale différente')
        return original
    except (KeyError,TypeError,UnicodeDecodeError,json.JSONDecodeError,zlib.error) as exc:
        raise CodecError('Trame invalide') from exc


def adaptive_frame(data, megabits_per_second=100, allowed_codecs=None, *, prune=False):
    """Choisit sur échantillon, sans entraînement IA ; estimation à vérifier sur bloc réel."""
    if not math.isfinite(megabits_per_second) or megabits_per_second<=0:
        raise CodecError('Débit strictement positif et fini requis')
    if len(data)>MAX_BLOCK:
        raise CodecError('Bloc trop grand')
    start=time.perf_counter()
    wire_bytes_per_second=megabits_per_second*1e6/8
    # Échantillons répartis et alignés ; aucun apprentissage sur le bloc complet.
    unit=16384
    if len(data)<=3*unit:
        sample=data
    else:
        middle=(len(data)//2//16)*16
        end=((len(data)-unit)//16)*16
        sample=data[:unit]+data[middle:middle+unit]+data[end:end+unit]
    multiplier=len(data)/max(1,len(sample))
    candidates=[]
    available = codecs() if allowed_codecs is None else [c for c in codecs() if c in allowed_codecs]
    if 'raw' not in available:
        raise CodecError('Le codec raw est requis')
    best_estimated=math.inf
    for codec in available:
        for width in ((1,) if codec=='raw' else (1,2,4,8,16)):
            begin=time.perf_counter()
            encoded=frame(sample,codec,width)
            encoding=time.perf_counter()-begin
            # Décoder ne peut qu'ajouter du temps à ce modèle. Une recette dont
            # la borne atteint déjà un candidat vérifié ne peut plus gagner.
            # Elle n'est pas retenue ; le décodage des blocs reçus reste intact.
            if prune:
                lower_bound=encoding*multiplier+len(encoded)*multiplier/wire_bytes_per_second
                if candidates and lower_bound>=best_estimated:
                    candidates.append({'codec':codec,'width':width,'estimated_seconds':lower_bound,
                                       'pruned':True,'estimate_is_lower_bound':True})
                    continue
            begin=time.perf_counter()
            restored=unframe(encoded)
            decoding=time.perf_counter()-begin
            if restored!=sample:
                raise CodecError('Transformation candidate non réversible')
            estimated=(encoding+decoding)*multiplier+len(encoded)*multiplier/wire_bytes_per_second
            candidates.append({'codec':codec,'width':width,'estimated_seconds':estimated})
            if prune:best_estimated=min(best_estimated,estimated)
    selected=min(candidates,key=lambda r:r['estimated_seconds'])
    selection=time.perf_counter()-start
    result,fallback=_encode_frame(data,selected['codec'],selected['width'],True)
    # Évite l'expansion en volume. Le temps de recherche déjà consommé reste comptabilisé.
    if fallback:
        selected={**selected,'codec':'raw','width':1,'fallback':'size expansion'}
    return result, {'selected':selected,'selection_seconds':selection,
                    'sample_bytes':len(sample),'candidates':candidates}


class AdaptiveEncoder:
    """Une recette par flux, reprofilage périodique et sonde sur chaque bloc.

    Le sélecteur estime le CPU des deux extrémités sur CETTE machine.
    L'estimation n'est pas une mesure de latence RDP.
    """
    def __init__(self, megabits_per_second=100, allowed_codecs=None, retune_every=16, *, prune=False):
        if not math.isfinite(megabits_per_second) or megabits_per_second<=0:
            raise CodecError('Débit strictement positif et fini requis')
        if type(retune_every) is not int or retune_every<1:
            raise CodecError('Intervalle invalide')
        self.rate=megabits_per_second
        self.allowed=codecs() if allowed_codecs is None else [c for c in codecs() if c in allowed_codecs]
        if 'raw' not in self.allowed:
            raise CodecError('Le codec raw est requis')
        self.interval=retune_every
        self.prune=prune
        self.recipe=None
        self.blocks=0
        self.searches=0
        self.reused=0

    def encode(self, data):
        if len(data)>MAX_BLOCK:
            raise CodecError('Bloc trop grand')
        retune=self.recipe is None or self.blocks%self.interval==0
        if not retune and len(data)>=4096:
            offsets=(0,(len(data)//2//16)*16,((len(data)-4096)//16)*16)
            sample=b''.join(data[o:o+4096] for o in offsets)
            codec,width=self.recipe
            if codec=='raw':
                probe='zstd1' if 'zstd1' in self.allowed else 'zlib1'
                if probe in self.allowed:
                    retune=min(len(compress(sample,probe)),len(compress(shuffle(sample,4),probe)))<len(sample)*0.90
            else:
                if len(compress(shuffle(sample,width),codec))>=len(sample)*0.98:
                    self.recipe=('raw',1)
        if retune:
            encoded,details=adaptive_frame(data,self.rate,self.allowed,prune=self.prune)
            selected=details['selected']
            self.recipe=(selected['codec'],selected['width'])
            self.searches+=1
        else:
            encoded,fallback=_encode_frame(data,*self.recipe,limit_expansion=True)
            if fallback:
                self.recipe=('raw',1)
            self.reused+=1
        self.blocks+=1
        return encoded
