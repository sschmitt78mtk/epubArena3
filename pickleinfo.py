import sys, types, pickle, collections
from pathlib import Path
import config

# stub ebooklib so pickle load works even without deps
ebooklib = types.ModuleType('ebooklib')
epub = types.ModuleType('ebooklib.epub')
setattr(ebooklib, 'epub', epub)
sys.modules['ebooklib'] = ebooklib
sys.modules['ebooklib.epub'] = epub

pkl_name = "bashpocketref2e.epub.pkl"  # change me
pkl = Path(config.PATH_PKL) / pkl_name
print('pkl:', pkl)

with open(pkl, 'rb') as f:
    data = pickle.load(f)

print('source chunks:', len(data.source.chunks))
print('translations:', len(data.translations))

for t in data.translations:
    print('\nTranslation:', t.modelname)
    print('  finished:', t.finished)
    print('  chunks:', len(t.chunks), 'of', t.number_of_chunks)
    types = collections.Counter(ch.chunktype for ch in t.chunks)
    print('  chunk types:', dict(types))
    same_as_source = 0
    for ch in t.chunks:
        src = data.source.chunk_exists(ch.chunk_id)
        if src and src.content == ch.content:
            same_as_source += 1
    print('  chunks identical to source:', same_as_source)
