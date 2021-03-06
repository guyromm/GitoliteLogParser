import argparse
import calendar
import datetime
import json
import os
from copy import deepcopy

import pygeoip
from mailer import MailMan


GIO_CITY = pygeoip.GeoIP('GeoLiteCity.dat')  # '/usr/share/GeoIP/GeoIP.dat')
GIO = pygeoip.GeoIP('/usr/share/GeoIP/GeoIP.dat')
READ_TPL = ['date', 'user', 'ip', 'raw_repo']
WRITE_PARTIAL_TPL = ['value5', 'value6', 'value7', 'value8',
                     'value9', 'value10']
WRITE_TPL = READ_TPL + WRITE_PARTIAL_TPL


def format_line(line, line_tpl):
    assert type(line) == dict, 'Error! Dict required.'
    formatted = []
    for key, value in line.iteritems():
        formatted.append(line_tpl % (key, value))
    formatted.append('\n')
    return '\n'.join(formatted)


def format_reports_dict(report):
    assert type(report) == dict, 'Error! Dict required.'
    formatted = []
    report_tpl = '\t%s: \n%s'
    line_tpl = '\t\t%s: %s;'
    for key, value in report.iteritems():
        formatted.append(report_tpl % (key, format_line(
            value, line_tpl)))
    return ''.join(formatted)


def format_errors(errors):
    assert type(errors) == list, 'Error! List required.'
    formatted_errors = []
    line_tpl = '\t%s: %s;'
    for error in errors:
        formatted_errors.append(format_line(error, line_tpl))
    return ''.join(formatted_errors)


def format_report(msg):
    """
    Report tpl
    """
    assert type(msg) == dict, 'Error! Dict required.'
    mykeys = ['users',
              'countries',
              'cities',
              'users_countries',
              'users_cities',
              'repositories',
              'users_repositories',
              'errors']  # ,'ips'
    report = ''
    for key in mykeys:
        if len(msg[key]):
            report += key.capitalize() + ': \n' + msg[key] + '\n'
    return report


def convdate(dt):
    daysdelta=None
    if dt == 'yesterday':
        daysdelta=1
    elif dt == 'today':
        daysdelta=0

    if daysdelta is not None:
        dt = (
            datetime.datetime.now() - datetime.timedelta(days=daysdelta))\
            .strftime('%Y-%m-%d')
    return dt


class GitoliteLogParser(object):
    parsed = dict()
    datestring = str()
    prev_datestring = None
    prev_summary = None
    users_repositories_tmp = []
    users_countries_tmp = []
    repositories_tmp = []
    countries_tmp = []

    root_dir = 'reports'

    parsed_tpl = {
        'countries': [],
        'cities': [],
        'ips': [],
        'users': [],
        'repositories': [],
        'report': {
            'errors': [],
            'countries': {},
            'cities': {},
            'repositories': {},
            'users': {},
            'ips': {},
            'users_repositories': {},
            'users_countries': {},
            'users_cities': {},
        }
    }
    key_plural = {
        'country': 'countries',
        'city': 'cities',
        'user': 'users',
        'ip': 'ips',
        'repo': 'repositories',
    }
    summary_tpl = {
        'countries': [],
        'cities': [],
        'users': [],
        'repositories': [],
        'ips': [],
        'users_countries': [],
        'users_cities': [],
        'users_repositories': [],
    }

    composite_keys = {
        'users_countries': ['user', 'country'],
        'users_cities': ['user', 'city'],
        'users_repositories': ['user', 'repo'],
    }

    def __init__(self, filepath, emails, date=None, new_load=None,nostate=False):
        if filepath=='yesterday': filepath = os.path.join('logs','gitolite-'+(datetime.datetime.now()-datetime.timedelta(days=1)).strftime('%Y-%m')+'.log')
        assert filepath and os.path.exists(filepath),"%s does not exist."%filepath
        self.log = open(filepath, 'r')
        self.line = str()
        self.emails = emails
        self.date = date
        self.new_load = new_load
        self.open_summary = False
        self.last_day = False
        self.date = convdate(self.date)
        self.nostate=nostate

        if date is not None and not self.nostate:
            self.summary = self._open_summary(convdate(date))
        elif new_load is None:
            self.open_summary = True
        else:
            self.summary = deepcopy(self.summary_tpl)

        if self.prev_summary is None and not self.open_summary:
            self.prev_summary = deepcopy(self.summary)

    def _data_inserter(self, data_object):
        for key, value in self.key_plural.iteritems():
            if self.line.get(key) \
                    and self.line[key] not in data_object[value]:
                data_object[value].append(self.line[key])

    def _open_summary(self, date):
        parse_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        date = parse_date - datetime.timedelta(1)
        date = date.strftime('%Y-%m-%d')
        filepath = '/'.join([self.root_dir, date, 'agg.json'])
        try:
            assert os.path.exists(filepath)
        except:
            if self.new_load:
                return deepcopy(self.summary_tpl)
            else:
                print "Previous summary (%s) not found, "\
                      "use --new-load for exclude this error" % (filepath)
                raise
        fp = open(filepath, 'r')
        return json.load(fp)

    def _make_composite_key(self, keys):
        partial_key = []
        for key in keys:
            if self.line.get(key):
                partial_key.append(self.line.get(key))
        if len(partial_key) < 2:
            partial_key.append('')
        return '_'.join(partial_key)

    def _insert_composite(self):
        for composite_key, value in self.composite_keys.iteritems():
            key = self._make_composite_key(value)
            if key is not None:
                if not key in self.summary.get(composite_key):
                    self.summary[composite_key].append(key)

    def insert_aggregation(self):
        self._data_inserter(self.parsed[self.datestring])

    def insert_summary(self):
        self._data_inserter(self.summary)
        self._insert_composite()

    def dump2json(self, object2save, date, filename):
        assert self.root_dir
        assert date
        assert filename
        path = '/'.join([self.root_dir, date, filename])
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        to_save = open(path, 'w')
        json.dump(object2save, to_save, indent=1)
        to_save.close()

    def _manage_state(self):
        print 'start new date', self.prev_datestring, self.datestring
        assert self.prev_datestring
        assert self.datestring
        # clean reports tmp
        self.users_repositories_tmp = []
        self.users_countries_tmp = []
        self.users_cities_tmp = []
        self.repositories_tmp = []
        self.countries_tmp = []
        self.cities_tmp = []

        # save summary
        self.dump2json(
            self.summary, self.prev_datestring, 'agg.json'
        )

        parsed = self.parsed.get(self.prev_datestring)
        report = parsed.get('report')
        # save report
        self.dump2json(report, self.prev_datestring, 'digest.json')
        del parsed['report']
        self.dump2json(
            self.parsed.get(self.prev_datestring),
            self.prev_datestring, 'summary.json'
        )

        if self.emails:
            report_tpl = self.parsed_tpl.get('report')
            msg = dict()
            subject = 'Gitolite log report - %s' % self.prev_datestring
            for key in report_tpl.keys():
                if key == 'errors':
                    data = format_errors(report.get(key, []))
                else:
                    data = format_reports_dict(report.get(key, {}))
                if not msg.get(key):
                    msg[key] = ''
                msg[key] = data
            MailMan.mail_send(
                MailMan(self.emails), subject, format_report(msg))

        self.prev_datestring = self.datestring
        self.prev_summary = deepcopy(self.summary)

        if not self.parsed.get(self.datestring):
            self.parsed[self.datestring] = deepcopy(self.parsed_tpl)

    def _simple_report(self, report):
        for key, value in self.key_plural.iteritems():
            if self.line.get(key) \
                    and self.line[key] not in self.prev_summary[value] \
                    and not report[value].get(self.line[key]):
                report[value][self.line[key]] = self.line

    def make_report(self):
        report = self.parsed[self.datestring]['report']
        self._simple_report(report)

        if self.line.get('error'):
            report['errors'].append(self.line)

        for composite_key, value in self.composite_keys.iteritems():
            key = self._make_composite_key(value)
            if key not in self.prev_summary.get(composite_key):
                report[composite_key][key] = self.line

    def parser(self, line):
        line = line.replace("\n", "").replace("'", "")
        splitted_line = line.split("\t")
        if len(splitted_line) == 4:
            self.line = dict(zip(READ_TPL, splitted_line))
        else:
            self.line = dict(zip(WRITE_TPL, splitted_line))

        self.parsed_date = datetime.datetime.strptime(self.line['date'],
                                                      '%Y-%m-%d.%H:%M:%S')
        self.datestring = self.parsed_date.strftime('%Y-%m-%d')
        last_day = calendar.mdays[self.parsed_date.month]

        if last_day == self.parsed_date.day:
            self.last_day = True

        if self.open_summary:
            self.summary = self._open_summary(convdate(self.datestring))
            self.open_summary = False
            self.prev_summary = deepcopy(self.summary)

        if self.date and self.datestring != self.date:
            if self.prev_datestring \
                    and len(self.parsed[self.prev_datestring]['countries']):
                self._manage_state()
            return

        # parse line section
        self.line['country'] = GIO.country_code_by_addr(self.line['ip'])
        rec = GIO_CITY.record_by_addr(self.line['ip'])
        if rec:
            self.line['city'] = rec['city']
        else:
            self.line['city'] = '?'

        self.line['date'] = self.parsed_date.strftime('%Y-%m-%d.%H:%M:%S')
        try:
            self.line['action'], \
                self.line['repo'] = self.line['raw_repo'].split(" ")
        except:
            self.line['error'] = self.line['raw_repo']
        del self.line['raw_repo']

        if self.prev_datestring is None:
            self.prev_datestring = self.datestring

        if not self.parsed.get(self.datestring):
            self.parsed[self.datestring] = deepcopy(self.parsed_tpl)

        if self.prev_datestring != self.datestring:
            self._manage_state()
        # insert data to aggretaion
        self.insert_aggregation()

        # time to make diff
        self.make_report()

        # insert data to summary
        self.insert_summary()

    def reader(self):
        for line in self.log.readlines():
            self.parser(line)

        if self.nostate: return False

        if self.date:
            date = datetime.datetime.strptime(self.date, '%Y-%m-%d')
            last_day = calendar.mdays[date.month]

            if last_day == date.day:
                self.last_day = True
            else:
                self.last_day = False
        if self.date and not self.last_day and self.date == self.datestring:
            self._manage_state()

        if self.last_day or not self.date:
            self._manage_state()
        return True

if __name__ == '__main__':
    optparser = argparse.ArgumentParser(
        description='Gitolie log file parser', add_help=True)

    optparser.add_argument('--filepath', action='store', dest='filepath',
                           help='path to gitolite log file', required=True)

    optparser.add_argument('--email', action='append', dest='emails',
                           help='emails for send reports')

    optparser.add_argument('--date', action='store', dest='date',
                           help='parse log row only this date.'
                           ' format: YYYY-MM-DD')

    optparser.add_argument('--new-load', action='store_true', dest='new_load',
                           default=None, help='Init new summary.')

    args = optparser.parse_args()

    # init and run parser
    parser = GitoliteLogParser(
        args.filepath, args.emails, args.date, args.new_load)
    parser.reader()
