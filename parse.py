import sys
import os
import re
import datetime
import yaml
import pygeoip
import json
from copy import deepcopy

gio = pygeoip.GeoIP('/usr/share/GeoIP/GeoIP.dat')
pathout = 'parsed'

root_dir = 'reports'


keys = {
    'user': 'users',
    'ip': 'ips',
    'repo': 'repos',
    'op': 'ops',
    'country': 'countries'
}


def mkaggarr():
    aggarr = {}
    for key in keys.values():
        aggarr[key]=[]
    return aggarr


def aggregate(prevagg, alertkeys, dt=None, fn=None):
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


        wfp = open(aggfn, 'w')
        yaml.dump(aggarr,wfp)


        wfp.close()

    return aggarr, alerts


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
    tagg = mkaggarr()
    for w in os.walk(wlkdir):
        for fn in w[2]:
            if not '.yaml' in fn:
                continue
            if upto.date() >= fn2date(fn, False).date():
                dagg, alerts = aggregate(
                    tagg, None, None, os.path.join(pathout, fn))
                aa = joinaggs(dagg, aa)
            else:
                pass
                #raise Exception('this is too late %s %s'%(upto,fn))
    return aa


def parsefile(fn, date=None):
    assert os.path.exists(fn)
    fp = open(fn, 'r')
    cnt = 0
    skp = 0
    alertkeys = {}
    while True:
        line = fp.readline()
        if not line:
            break
        #get the line values
        vals = parseline(line)
        #get an agg of all values before (to compare)
        if date and vals['stamp'].date() != date.date():
            #print 'date mismatch %s %s'%(date,vals['stamp'])
            skp += 1
            continue
        dstr = vals['stamp'].strftime('%Y-%m-%d')
        if dstr not in alertkeys:
            alertkeys[dstr] = []
        totagg = getaggs(upto=vals['stamp'] - datetime.timedelta(days=1))
        #agg the new line
        lagg, alerts = aggregate(totagg, alertkeys[dstr], vals)
        if len(alerts):
            for a in alerts:
                print 'ALERT: ', a[0], a[1]  # ,vals['raw']
        cnt += 1
    print 'parsed %s lines, skipped %s ;  in %s' % (cnt, skp, fn)

groupnames = ['stamp', 'user', 'ip', 'op_repo']


def mkre():
    matchunit = r'(?P<%s>[^\t]+)'
    units = [matchunit % name for name in groupnames]
    restr = '^' + r'\t'.join(units) + r'(|(?P<extra>(.*)))\n$'
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


read_tpl = ['date', 'user', 'ip', 'raw_repo']
write_partial_tpl = ['value5', 'value6', 'value7', 'value8',
                     'value9', 'value10']
write_tpl = read_tpl + write_partial_tpl
parsed_tpl = {
    'countries': [],
    'ips': [],
    'users': [],
    'repositories': [],
    'errors': [],
    'report': {
        'countries': [],
        'repositories': [],
        'users': [],
    }
}


def dump2json(object2save, date, filename):
    path = '/'.join([root_dir, date, filename])
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    to_save = open(path, 'w')
    json.dump(object2save, to_save, indent=1)
    to_save.close()


def parser(filepath, date=None):
    assert os.path.exists(filepath)
    log = open(filepath, 'r')
    cnt = 0
    parsed = dict()
    prev_datestring = None
    prev_summary = None

    if date is not None:
        # implement load summary by date from file
        pass
    else:
        summary = {
            'countries': [],
            'users': [],
            'repositories': [],
            'ips': [],
        }

    for line in log.readlines():
        line = line.replace("\n", "")
        line = line.replace("'", "")
        cnt += 1
        splitted_line = line.split("\t")
        if len(splitted_line) == 4:
            line = dict(zip(read_tpl, splitted_line))
        else:
            line = dict(zip(write_tpl, splitted_line))

        # parse line section
        line['country'] = gio.country_code_by_addr(line['ip'])
        line['date'] = datetime.datetime.strptime(line['date'],
                                                  '%Y-%m-%d.%H:%M:%S')
        try:
            line['action'], line['repo'] = line['raw_repo'].split(" ")
        except:
            line['error'] = line['raw_repo']
        del line['raw_repo']
        datestring = line['date'].strftime('%Y:%m:%d')

        if prev_datestring is None:
            prev_datestring = datestring

        if prev_summary is None:
            prev_summary = deepcopy(summary)

        if prev_datestring != datestring:
            print 'start new date', prev_datestring, datestring
            # save summary
            dump2json(summary, prev_datestring, 'summary.json')
            # save parsed
            dump2json(parsed.get(prev_datestring),
                      prev_datestring, 'parsed.json')

            prev_datestring = datestring
            prev_summary = deepcopy(summary)

        if not parsed.get(datestring):
            parsed[datestring] = deepcopy(parsed_tpl)

        line['date'] = line['date'].strftime('%Y-%m-%d.%H:%M:%S')

        # insert data to aggretaion
        if line['country'] not in parsed[datestring]['countries']:
            parsed[datestring]['countries'].append(line['country'])

        if line['ip'] not in parsed[datestring]['ips']:
            parsed[datestring]['ips'].append(line['ip'])

        if line['user'] not in parsed[datestring]['users']:
            parsed[datestring]['users'].append(line['user'])

        if line.get('repo') \
                and line['repo'] not in parsed[datestring]['repositories']:
            parsed[datestring]['repositories'].append(line['repo'])

        if line.get('error'):
            parsed[datestring]['errors'].append(line)

        # time to make diff
        line_repr = 'User: %s, Country: %s, IP: %s, Repository: %s' \
                    % (line['user'], line['country'], line['ip'],
                       line.get('repo'))

        if line['country'] not in prev_summary['countries'] \
                and line_repr not in parsed[datestring]['report']['countries']:
            parsed[datestring]['report']['countries'].append(line_repr)

        if line['user'] not in prev_summary['users'] \
                and line_repr not in parsed[datestring]['report']['users']:
            parsed[datestring]['report']['users'].append(line_repr)

        if line.get('repo') \
                and line['repo'] not in prev_summary['repositories'] \
                and line_repr \
                not in parsed[datestring]['report']['repositories']:
            parsed[datestring]['report']['repositories'].append(line_repr)

        # insert data to summary
        if line['country'] not in summary['countries']:
            summary['countries'].append(line['country'])

        if line['user'] not in summary['users']:
            summary['users'].append(line['user'])

        if line['ip'] not in summary['ips']:
            summary['ips'].append(line['ip'])

        if line.get('repo') \
                and line['repo'] not in summary['repositories']:
            summary['repositories'].append(line['repo'])


if __name__ == '__main__':
    #parsefile(sys.argv[1], date)
    parser(sys.argv[1])
