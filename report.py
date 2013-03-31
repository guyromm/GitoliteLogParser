#!/usr/bin/env python
import json
from commands import getstatusoutput as gso
import os
import datetime
import argparse
logs_dir = 'logs/'
from parse import GitoliteLogParser

class Report(object):
    def cmdrun(self):
        optparser = argparse.ArgumentParser(
            description='Gitolie report generator', add_help=True)
        optparser.add_argument('--from', action='store', dest='parse_from',
                               help='parse log from this date.'
                               ' format: YYYY-MM-DD',required=True)
        optparser.add_argument('--to', action='store', dest='parse_to',
                               help='parse log until this date.'
                               ' format: YYYY-MM-DD',required=True)
        optparser.add_argument('--outfile',action='store',dest='save_to',
                               help='.html file to save to.',default='rep.html')
        self.args = args = optparser.parse_args()
        
        fr = datetime.datetime.strptime(args.parse_from,'%Y-%m-%d')
        to = datetime.datetime.strptime(args.parse_to,'%Y-%m-%d')
        
        i =fr
        while i<=to:
            fp = os.path.join(logs_dir,'gitolite-%s-%02d.log'%(i.year,i.month))
            print '%s / %s'%(fp,i)
            glp = GitoliteLogParser(fp,[],i.strftime('%Y-%m-%d'),new_load=True,nostate=True)
            glp.reader()
            urep = glp.summary['users_repositories']
            if not self.mind or i<=self.mind: self.mind=i
            if not self.maxd or i>=self.maxd: self.maxd=i
            self.aggregate(urep,i.strftime('%Y-%m-%d'))
            i+=datetime.timedelta(days=1)
        #2nd pass to make sure we have zeros all over.
        for u in self.overtime:
            i = fr
            while i<=to:
                dt = i.strftime('%Y-%m-%d')
                if dt not in self.overtime[u]: self.overtime[u][dt]=0
                i+=datetime.timedelta(days=1)
        self.report()

    times = {}
    overtime={}
    repoovertime={}
    total={}
    mind=None
    maxd=None
    def aggregate(self,urep,dtstr):
        for ur in urep:
            ur = ur.replace('same_git','SAMEGIT')
            try:
                u,r = ur.split('_')
            except ValueError:
                print 'could not parse %s'%ur
                continue

            if u not in self.times: self.times[u]=0
            self.times[u]+=1

            if u not in self.overtime: self.overtime[u]={}
            if dtstr not in self.overtime[u]: self.overtime[u][dtstr]=0
            self.overtime[u][dtstr]+=1

            if u not in self.repoovertime: self.repoovertime[u]={}
            if dtstr not in self.repoovertime[u]: self.repoovertime[u][dtstr]={}
            if r not in self.repoovertime[u][dtstr]: self.repoovertime[u][dtstr][r]=0
            self.repoovertime[u][dtstr][r]+=1

            if dtstr not in self.total: self.total[dtstr]=0
            self.total[dtstr]+=1
    def report(self):
        r = open('report.html','r').read()
        r=r.replace('${TIMES}',json.dumps(self.times.items()))
        r=r.replace('${OVERTIME}',json.dumps(self.overtime))
        assert '${' not in r
        fp = open(self.args.save_to,'w') ; fp.write(r)  ; fp.close()


if __name__=='__main__':
    r = Report()
    r.cmdrun()

    


