"""
===============================================================================
Use pysam model to calculate the AS from bam file
===============================================================================
Author : Shujia Huang
Date   : 2014-03-25 14:29:08
"""
import os

def LoadFaSeq(file, refId = 'ALL'):

    if file[-3:] == '.gz':
        I = os.popen('gzip -dc %s' % file)
    else :
        I = open(file)

    fa, id = {}, ''
    isContinue, isBreak = True, False
    while 1:

        lines = I.readlines(100000)
        if not lines or isBreak: break

        for line in lines:

            line = line.strip('\n')
            if len(line) == 0: continue

            if line[0] == '>':

                id = line.split()[0][1:]
                if id in fa:
                    raise ValueError('# [ERROR] Catch Duplcation name in file %s at id %s' % (file, id))

                # Should set to break after getting fa[id] if refId != 'ALL'
                if refId != 'ALL' and not isContinue: isBreak = True
                if refId != 'ALL' and id != refId: 
                    isContinue = True
                else:
                    isContinue = False
                    fa[id] = []

            else:
                if not isContinue: fa[id].append(line)

    for k, v in fa.items(): fa[k] = ''.join(v)

    return fa

def SumMismatchQuality(readSeq, readQual, tarSeq):

    # [Debug]
    #print >> sys.stderr, '%%%%%',readSeq,'\n%%%%%',tarSeq,'\n'

    zr, rn = 0, 0
    for i in range(min(len(readSeq), len(tarSeq))):
        if tarSeq[i].lower() != readSeq[i].lower():
            rn += 1
            zr += (ord(readQual[i]) - 33)

    return zr, rn

def Ref2QryPos(rstart, rpos, cigar):
# rstart is 0-base
# rpos   is 1-base
    cigarDict = {0:'M', 1:'I', 2:'D', 3:'N', 4:'S', 5:'H', 6:'P', 7:'=', 8:'X'}
    rmaplen, qpos = 0, 0
    for m in ''.join(cigarDict[type] * size for type,size in cigar): # cigar string
        if m in 'MXNP=D': rmaplen += 1
        if m in 'MIS=X' : qpos    += 1
        if rstart + rmaplen == rpos: break

    return qpos # 0-base

#def Align(samInHandle, samOutHandle, fa, id, position, varId, refseq, altseq, mapq = 20):
def Align(samInHandle, fa, id, position, varId, refseq, altseq, mapq = 20):
    """ 
    position is the left break point of the variants
    And the position should be 1-base for convenience. 
    Because I use something like fa[id][position-1] to get bases from fa string
    """
    if position < 1:
        raise ValueError('[ERROR] The reference position is not 1-base: %r' % position)

    if id not in fa: 
        raise ValueError('#[ERROR] The reference did not contain %s' % id)

    rr,aa,com,diff = 0,0,0,0
    for pileup in samInHandle.pileup(id, position-1, position): 

        pos = pileup.pos + 1 # 0-base index to 1-base index
        if pos != position: continue

        for read in [al for al in pileup.pileups if al.alignment.mapq >= mapq]: 
            
            refPos = read.alignment.pos - read.alignment.qstart  # 0-base 
            # Next if the position is 2bp near the end of the reads
            if position > refPos + read.alignment.rlen - 2: continue

            q = Ref2QryPos(read.alignment.pos, position, read.alignment.cigar)
            if q > read.alignment.rlen:
                raise ValueError('#[BUG] The query position(%r) is > read length(%r)' 
                                 % (q, read.alignment.rlen))
            if q == read.alignment.rlen: continue

            refSeq = fa[id][position:refPos+read.alignment.rlen] 
            qrySeq = altseq + fa[id][position+len(refseq)-1:position+len(refseq)+read.alignment.rlen-q]

            # [Debug]
            # print '[POS]', id, pos, read.alignment.pos+1, '\n[QRY]', fa[id][refPos:position], qrySeq, read.alignment.qstart, q,'\n[TAR]',fa[id][refPos:position],refSeq,'\n[SEQ]', read.alignment.seq, read.alignment.cigar, read.alignment.cigarstring, read.alignment.is_secondary, '\n'

            zr, _ = SumMismatchQuality(read.alignment.seq[q:], read.alignment.qual[q:], refSeq) # Reference
            za, _ = SumMismatchQuality(read.alignment.seq[q:], read.alignment.qual[q:], qrySeq) # Alternate

            if zr == 0 and za == 0: 
                com += 1 # Common perfect
            elif zr == 0 and za  > 0: 
                rr  += 1 # Reference perfect
            elif zr  > 0 and za == 0: 
                aa  += 1 # Alternate perfect
            else: 
                diff += 1 # All im-perfect

            #read.alignment.tags += [('ZJ', varId)] + [('ZR', zr)] + [('ZA', za)] # Not output to save the store
            #samOutHandle.write(read.alignment) # Not output to save the store

    return rr,aa,com,diff

##################### End ##############################################











