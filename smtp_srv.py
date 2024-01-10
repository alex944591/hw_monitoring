#!/usr/bin/python3

import subprocess
from datetime import datetime
import asyncore
from smtpd import SMTPServer
import re

class EmlServer(SMTPServer):
    no = 0
    santry_ip = '172.17.74.8'
    regexp_san = r'(?:.*)\n(?P<Subject>Subject: .+)(?:\n.*)+(?P<NodeID>Node ID: .+)(?:\n.*)+(?P<Message>Event Message: .+)'

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        ZABBIX_SRV = '172.17.74.49'
        ZABBIX_PORT = '10051'


        filename = '%s-%d.eml' % (datetime.now().strftime('%Y%m%d%H%M%S')+f'_{peer[0]}',self.no)

        with open(filename, 'wb') as f:
            f.write(data)
            print('%s saved.' % filename)

        with open(filename, 'r') as f:
            mail = f.read()


        if peer[0] == self.santry_ip:
            match = re.search(self.regexp_san, mail)

            if match:
                Subject = match.group('Subject')
                NodeID = match.group('NodeID')
                Message = match.group('Message')

                subprocess.run(['zabbix_sender', '-z', ZABBIX_SRV, '-p',
                                ZABBIX_PORT, '-s', 'SANTRY', '-k', 'storage', '-o', f'{Subject}, {NodeID}, {Message}'],
                               stdout=subprocess.PIPE)

        self.no += 1

def run():
    EmlServer(('0.0.0.0', 25), remoteaddr=('', 0))
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run()