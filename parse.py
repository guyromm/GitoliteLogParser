import argparse
import datetime
import json
import os
from copy import deepcopy

import pygeoip
from mailer import MailMan


GIO = pygeoip.GeoIP('/usr/share/GeoIP/GeoIP.dat')
READ_TPL = ['date', 'user', 'ip', 'raw_repo']
WRITE_PARTIAL_TPL = ['value5', 'value6', 'value7', 'value8',
                     'value9', 'value10']
WRITE_TPL = READ_TPL + WRITE_PARTIAL_TPL


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
        'ips': [],
        'users': [],
        'repositories': [],
        'report': {
            'errors': [],
            'countries': {},
            'repositories': {},
            'users': {},
            'ips': {},
            'users_repositories': {},
            'users_countries': {},
        }
    }
    key_plural = {
        'country': 'countries',
        'user': 'users',
        'ip': 'ips',
        'repo': 'repositories',
    }
    summary_tpl = {
        'countries': [],
        'users': [],
        'repositories': [],
        'ips': [],
    }

    def __init__(self, filepath, emails, date=None):
        assert os.path.exists(filepath)
        self.log = open(filepath, 'r')
        self.line = str()
        self.emails = emails
        self.date = date
        if date is not None:
            self.summary = self._open_summary()
        else:
            self.summary = deepcopy(self.summary_tpl)

        if self.prev_summary is None:
            self.prev_summary = deepcopy(self.summary)

    def _data_inserter(self, data_object):
        for key, value in self.key_plural.iteritems():
            if self.line.get(key) \
                    and self.line[key] not in data_object[value]:
                data_object[value].append(self.line[key])

    def _open_summary(self):
        parse_date = datetime.datetime.strptime(self.date, '%Y-%m-%d')
        date = parse_date - datetime.timedelta(1)
        date = date.strftime('%Y-%m-%d')
        filepath = '/'.join([self.root_dir, date, 'summary.json'])
        try:
            assert os.path.exists(filepath)
        except:
            return deepcopy(self.summary_tpl)
        fp = open(filepath, 'r')
        return json.load(fp)

    def insert_aggregation(self):
        self._data_inserter(self.parsed[self.datestring])

    def insert_summary(self):
        self._data_inserter(self.summary)

    def dump2json(self, object2save, date, filename):
        path = '/'.join([self.root_dir, date, filename])
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        to_save = open(path, 'w')
        json.dump(object2save, to_save, indent=1)
        to_save.close()

    def _format_reports_dict(self, report):
        assert type(report) == dict, 'Error! Dict required.'
        formatted = []
        report_tpl = '\t%s: \n%s'
        line_tpl = '\t\t%s: %s;'
        for key, value in report.iteritems():
            formatted.append(report_tpl % (key, self._format_line(
                value, line_tpl)))
        return ''.join(formatted)

    def _format_errors(self, errors):
        assert type(errors) == list, 'Error! List required.'
        formatted_errors = []
        line_tpl = '\t%s: %s;'
        for error in errors:
            formatted_errors.append(self._format_line(error, line_tpl))
        return ''.join(formatted_errors)

    def _format_line(self, line, line_tpl):
        assert type(line) == dict, 'Error! Dict required.'
        formatted = []
        for key, value in line.iteritems():
            formatted.append(line_tpl % (key, value))
        formatted.append('\n')
        return '\n'.join(formatted)

    def _format_report(self, msg):
        """
        Report tpl
        """
        assert type(msg) == dict, 'Error! Dict required.'
        report = 'Errors: \n%(errors)s\n'\
                 'Users: \n%(users)s\n'\
                 'Countries: \n%(countries)s\n'\
                 'Users countries: \n%(users_countries)s\n'\
                 'Repositories: \n%(repositories)s\n'\
                 'Users repositories: \n%(users_repositories)s\n'\
                 'IPS: \n%(ips)s\n' % msg
        return report

    def _manage_state(self):
        print 'start new date', self.prev_datestring, self.datestring
        # clean reports tmp
        self.users_repositories_tmp = []
        self.users_countries_tmp = []
        self.repositories_tmp = []
        self.countries_tmp = []

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
        self._format_reports_dict(report.get('countries', []))
        if self.emails:
            report_tpl = self.parsed_tpl.get('report')
            msg = dict()
            subject = 'Gitolite log report - %s' % self.prev_datestring
            for key in report_tpl.keys():

                if key == 'errors':
                    data = self._format_errors(report.get(key, []))
                else:
                    data = self._format_reports_dict(report.get(key, {}))
                if not msg.get(key):
                    msg[key] = ''
                msg[key] = data

            MailMan.mail_send(
                MailMan(self.emails), subject, self._format_report(msg))

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

        if self.line.get('repo') \
                and self.line['user'] not in self.prev_summary['users'] \
                and self.line['repo'] not in self.prev_summary['repositories']\
                and self.line['repo'] not in self.repositories_tmp \
                and self.line['user'] not in self.users_repositories_tmp:
            key = '_'.join([self.line['user'], self.line['repo']])
            report['users_repositories'][key] = self.line
            self.users_repositories_tmp.append(self.line['user'])
            self.repositories_tmp.append(self.line['repo'])

        if self.line['user'] not in self.prev_summary['users'] \
                and self.line['country'] not in self.prev_summary['countries']\
                and self.line['country'] not in self.countries_tmp \
                and self.line['user'] not in self.users_countries_tmp:
            key = '_'.join([self.line['user'], self.line['country']])
            report['users_countries'][key] = self.line
            self.users_countries_tmp.append(self.line['user'])
            self.countries_tmp.append(self.line['country'])

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

        if self.date and self.datestring != self.date:
            if self.prev_datestring \
                    and len(self.parsed[self.prev_datestring]['countries']):
                self._manage_state()
            return

        # parse line section
        self.line['country'] = GIO.country_code_by_addr(self.line['ip'])

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


if __name__ == '__main__':
    optparser = argparse.ArgumentParser(
        description='Gitolie log file parser', add_help=True)

    optparser.add_argument('--filepath', action='store', dest='filepath',
                           help='path to gitolite log file')

    optparser.add_argument('--email', action='append', dest='emails',
                           help='emails for send reports')

    optparser.add_argument('--date', action='store', dest='date',
                           help='parse log row only this date.'
                           ' format: YYYY-MM-DD')
    args = optparser.parse_args()

    # init and run parser
    parser = GitoliteLogParser(args.filepath, args.emails, args.date)
    parser.reader()
