import sys,os,re,datetime,yaml
import pygeoip

gio = pygeoip.GeoIP('GeoIP.dat')
pathout = 'parsed'

keys = {'user':'users','ip':'ips','repo':'repos','op':'ops','country':'countries'}
def mkaggarr():
    aggarr = {}
    for key in keys.values(): aggarr[key]=[]
    return aggarr

def aggregate(prevagg,alertkeys,dt=None,fn=None):
    assert dt or fn,"i need a file or line to proceed"
    if dt:
        dtstr = '%s-%s-%s'%(dt['stamp'].year,dt['stamp'].month,dt['stamp'].day)
    else:
        dtstr = fn2date(fn)

    aggfn = os.path.join(pathout,dtstr+'.yaml')

    if os.path.exists(aggfn):
        fp = open(aggfn,'r')
        aggarr = yaml.load(fp)
    else:
        print 'creating a new file %s'%aggfn
        aggarr = mkaggarr()    
        
    alerts=[]
    if dt:
        for singular,plural in keys.items():
            alertkey = '%s-%s'%(singular,dt[singular])
            if dt[singular] not in prevagg[plural] and alertkey not in alertkeys:
                alerts.append([singular,dt[singular],dt['raw']])
                aggarr[plural].append(dt[singular])
                alertkeys.append(alertkey)
            else:
                pass
                #print 'checking %s %s; is in %s or %s'%(singular,dt[singular],prevagg[plural],aggarr[plural])


        wfp = open(aggfn,'w')
        yaml.dump(aggarr,wfp)


        wfp.close()

    return aggarr,alerts
    
def fn2date(fn,getstr=True):
    bn = os.path.basename(fn)
    rt= bn.split('.yaml')[0]
    if getstr: return rt
    return datetime.datetime.strptime(rt,'%Y-%m-%d')
    
def joinaggs(a1,a2):
    for k in keys.values():
        for item in a2[k]:
            a1[k].append(item)
    return a1


def getaggs(upto):
    aa = mkaggarr()
    wlkdir = pathout
    #raise Exception('getting all aggs up to %s: %s'%(upto,wlkdir))
    tagg=mkaggarr()
    for w in os.walk(wlkdir):
        for fn in w[2]:
            if not '.yaml' in fn: continue
            if upto.date()>=fn2date(fn,False).date():
                dagg,alerts = aggregate(tagg,None,None,os.path.join(pathout,fn))
                aa = joinaggs(dagg,aa)
            else:
                pass
                #raise Exception('this is too late %s %s'%(upto,fn))
    return aa

def parsefile(fn,date=None):
    assert os.path.exists(fn)
    fp = open(fn,'r')
    cnt=0 ; skp=0
    alertkeys = {}
    while True:
        line = fp.readline()
        if not line: break
        #get the line values
        vals = parseline(line)
        #get an agg of all values before (to compare)
        if date and vals['stamp'].date()!=date.date():
            #print 'date mismatch %s %s'%(date,vals['stamp'])
            skp+=1
            continue
        dstr= vals['stamp'].strftime('%Y-%m-%d')
        if dstr not in alertkeys: alertkeys[dstr]=[]
        totagg = getaggs(upto=vals['stamp']-datetime.timedelta(days=1))
        #agg the new line
        lagg,alerts = aggregate(totagg,alertkeys[dstr],vals)
        if len(alerts): 
            for a in alerts:
                print 'ALERT: ',a[0],a[1]#,vals['raw']

        
        cnt+=1
    print 'parsed %s lines, skipped %s ;  in %s'%(cnt,skp,fn)

groupnames = ['stamp','user','ip','op_repo']
def mkre():
    matchunit = r'(?P<%s>[^\t]+)'
    units = [matchunit%name for name in groupnames]
    restr = '^'+r'\t'.join(units)+r'(|(?P<extra>(.*)))\n$'
    lpre = re.compile(restr)
    return lpre
lpre = mkre()

    
def parseline(line):
    rt = {}
    res = lpre.search(line)
    if not res:
        raise Exception(line)
    for k in groupnames: 
        rt[k]=res.group(k)
    if not re.compile('^git-').search(rt['op_repo']):
        rt['op']='ERROR'
        rt['repo']='ERROR'
    else:
        oprepo = rt['op_repo'].split(' ')
        rt['op']=oprepo[0]
        rt['repo']=' '.join(oprepo[1:]) #'/'.join((' '.join(oprepo[1:])).split('/')[1:])
    ostamp = rt['stamp']
    rt['stamp']=datetime.datetime.strptime(rt['stamp'],'%Y-%m-%d.%H:%M:%S')
    rt['country'] = gio.country_code_by_addr(rt['ip'])
    del rt['op_repo']
    #raise Exception(rt['stamp'],ostamp)
    #print rt
    rt['raw']=line.strip()
    return rt

if __name__=='__main__':
    if len(sys.argv)>2:
        date = datetime.datetime.strptime(sys.argv[2],'%Y-%m-%d')
    else:
        date = None
    parsefile(sys.argv[1],date)
    
