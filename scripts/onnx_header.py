"""Print ONNX graph I/O, opset and op histogram from an APK entry; never prints weights."""
import sys, zipfile, collections

def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s; s += 7
        if c < 0x80:
            return r, i

def fields(b):
    i, n = 0, len(b)
    while i < n:
        k, i = varint(b, i); f, t = k >> 3, k & 7
        if t == 0:
            v, i = varint(b, i)
        elif t == 1:
            v = b[i:i + 8]; i += 8
        elif t == 5:
            v = b[i:i + 4]; i += 4
        elif t == 2:
            l, i = varint(b, i); v = b[i:i + l]; i += l
        else:
            raise ValueError(t)
        yield f, v

DT = {1: 'float32', 2: 'uint8', 3: 'int8', 6: 'int32', 7: 'int64', 10: 'float16', 9: 'bool'}

def vinfo(b):
    name, et, dims = '', None, []
    for f, v in fields(b):
        if f == 1: name = v.decode()
        if f == 2:
            for f2, v2 in fields(v):
                if f2 == 1:
                    for f3, v3 in fields(v2):
                        if f3 == 1: et = DT.get(v3, v3)
                        if f3 == 2:
                            for f4, v4 in fields(v3):
                                if f4 == 1:
                                    d = '?'
                                    for f5, v5 in fields(v4):
                                        d = v5 if f5 == 1 else v5.decode()
                                    dims.append(d)
    return f"{name}: {et} {dims}"

z = zipfile.ZipFile(sys.argv[1])
for entry in sys.argv[2:]:
    b = z.read(entry)
    print('==', entry, len(b))
    for f, v in fields(b):
        if f == 1: print(' ir', v)
        if f in (2, 3): print(' producer' if f == 2 else ' producer_ver', v.decode(errors='replace'))
        if f == 8: print(' opset', dict((ff, vv if isinstance(vv, int) else vv.decode()) for ff, vv in fields(v)))
        if f == 7:
            ops = collections.Counter(); inits = 0
            for g, gv in fields(v):
                if g == 1:
                    for nf, nv in fields(gv):
                        if nf == 4: ops[nv.decode()] += 1
                if g == 5: inits += 1
                if g == 11: print('  in ', vinfo(gv))
                if g == 12: print('  out', vinfo(gv))
            print('  initializers', inits, 'nodes', sum(ops.values()))
            print('  ops', dict(ops.most_common()))
