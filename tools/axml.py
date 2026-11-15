import struct

def r_len8(b,o):
    n=b[o]; o+=1
    if n&0x80:
        n=((n&0x7F)<<8)|b[o]; o+=1
    return n,o

def r_len16(b,o):
    n=struct.unpack('<H',b[o:o+2])[0]; o+=2
    if n&0x8000:
        n=((n&0x7FFF)<<16)|struct.unpack('<H',b[o:o+2])[0]; o+=2
    return n,o

class Pool:
    def __init__(self,b,off):
        t,hs,sz=struct.unpack('<HHI',b[off:off+8])
        self.off=off; self.hs=hs; self.size=sz
        self.count,self.styc,self.flags,self.strstart,self.stylestart=struct.unpack('<IIIII',b[off+8:off+28])
        self.offsets=[struct.unpack('<I',b[off+28+i*4:off+32+i*4])[0] for i in range(self.count)]
        self.strs=[]
        for i,o in enumerate(self.offsets):
            p=off+self.strstart+o
            if self.flags&0x100:
                _,p=r_len8(b,p); nbytes,p=r_len8(b,p)
                self.strs.append(b[p:p+nbytes].decode('utf-8','replace'))
            else:
                n,p=r_len16(b,p)
                self.strs.append(b[p:p+n*2].decode('utf-16-le','replace'))
    def get(self,i):
        if i==0xFFFFFFFF or i>=self.count: return None
        return self.strs[i]

def walk(b):
    total=struct.unpack('<I',b[4:8])[0]
    off=8; pool=None; out=[]
    while off<total:
        t,hs,sz=struct.unpack('<HHI',b[off:off+8])
        if t==0x0001:
            pool=Pool(b,off)
            out.append(('POOL',off,sz,pool.count,hex(pool.flags)))
        elif t==0x0180:
            out.append(('RESMAP',off,sz,0,None))
        elif t in (0x0100,0x0101):
            ln,cm,pref=struct.unpack('<III',b[off+8:off+20])
            ns,nm=struct.unpack('<II',b[off+16:off+24]) if t==0x0100 else (0,0)
            out.append(('NS' if t==0x0100 else 'ENDNS',off,sz,pool.get(nm) if pool else None,pool.get(ns) if pool else None))
        elif t==0x0102:
            ln,cm=struct.unpack('<II',b[off+8:off+16])
            ns,nm,astart,asize,acnt,idx,cidx,sidx=struct.unpack('<IIHHHHHH',b[off+16:off+36])
            out.append(('START',off,sz,pool.get(nm),acnt))
        elif t==0x0103:
            ln,cm,ns,nm=struct.unpack('<IIII',b[off+8:off+24])
            out.append(('END',off,sz,pool.get(nm),None))
        else:
            out.append(('UNK',off,sz,t,None))
            break
        off+=sz
    return out,pool
