"""Compatibilité avec les premiers essais du laboratoire UTCL1."""
from ultra.compression import (MAGIC, MAX_BLOCK, MAX_FRAME, CodecError, ZSTD,
                               Zstd, AdaptiveEncoder, adaptive_frame, codecs,
                               compress, decompress, frame, shuffle, unframe)
