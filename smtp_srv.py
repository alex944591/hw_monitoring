#!/usr/bin/python3

import subprocess
from datetime import datetime
import asyncore
from smtpd import SMTPServer
import re
import logging
import os
import base64

# Находим абсолютный путь к каталогу, где находится скрипт
script_directory = os.path.dirname(os.path.abspath(__file__))

# Создаем поддиректории, если они не существуют
emails_directory = os.path.join(script_directory, 'emails')
log_directory = os.path.join(script_directory, 'log')

for directory in [emails_directory, log_directory]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Настройки логирования
log_file_path = os.path.join(log_directory, 'email_server.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmlServer(SMTPServer):
    no = 0
    santry_ip = '172.17.74.8'
    vcsa_ip = '172.17.74.7'
    c7000 = ['172.20.36.8', '172.20.36.9', '172.20.36.38', '172.20.36.39']

    regexp_san = r'(?:.*)\n(?P<Subject>Subject: .+)(?:\n.*)+(?P<NodeID>Node ID: .+)(?:\n.*)+(?P<Message>Event Message: .+)'
    regexp_vcsa = r'(?:Subject: =\?utf-8\?B\?)(?P<Subject>.+)\n((:?.+)\n)*\n(?P<Message>.+)'
    regexp_c7000 = r'(?P<Subject>Subject: .+)\n(?P<From>From: .+)\n(?:.+\n)*\n(?:EVENT \(.+\): (?P<Event>.+))'

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        ZABBIX_SRV = '172.17.74.49'
        ZABBIX_PORT = '10051'

        print(peer[0])

        filename = os.path.join(emails_directory, '%s-%d.eml' % (datetime.now().strftime('%Y%m%d%H%M%S')+f'_{peer[0]}', self.no))

        with open(filename, 'wb') as f:
            f.write(data)
            logging.info('%s saved.' % filename)

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
                logging.info('Data sent to Zabbix: %s, %s, %s' % (Subject, NodeID, Message))


        if peer[0] in self.c7000:
            match = re.search(self.regexp_c7000, mail)
            print('In c7000 section')

            if match:
                print('Im match section of c7000')
                Subject = match.group('Subject')
                From = match.group('From')
                Event = match.group('Event')

                res = subprocess.run(['zabbix_sender', '-z', ZABBIX_SRV, '-p',
                                ZABBIX_PORT, '-s', 'HPE', '-k', 'c7000', '-o', f'{Subject}, {From}, {Event}'],
                               stdout=subprocess.PIPE)
                print(res)
                logging.info('Data sent to Zabbix: %s, %s, %s' % (Subject, From, Event))


        if peer[0] == self.vcsa_ip:
            regexp_description = r'(?P<Description>Description: \n.+)'
            match = re.search(self.regexp_vcsa, mail)

            if match:
                res = match.groupdict()
                Subject = base64.b64decode(res['Subject']).decode('utf-8')
                Message = base64.b64decode(res['Message']).decode('utf-8')

                sub_l, sub_r= match.span('Subject')
                mes_l, mes_r= match.span('Message')

                mail_decoded = mail[:sub_l-1]+'\n'+Subject+mail[sub_r+1:mes_l-1]+'\n'+Message+'\n'+mail[mes_r+1:]

                print(mail_decoded)
                filename += '_utf8'

                with open(filename, 'w') as f:
                    f.write(mail_decoded)
                    logging.info('%s saved.' % filename)

                match = re.search(regexp_description, Message)

                if match:
                    Description = match.group('Description')
                    print(f'{Subject}, {Description}')

                    subprocess.run(['zabbix_sender', '-z', ZABBIX_SRV, '-p',
                                    ZABBIX_PORT, '-s', 'VCSA', '-k', 'vcsa', '-o', f'{Subject}, {Description}'],
                                   stdout=subprocess.PIPE)
                    logging.info('Data sent to Zabbix: %s, %s' % (Subject, Description))

        self.no += 1

def run():
    logging.info('SMTP Server started.')
    EmlServer(('0.0.0.0', 25), remoteaddr=('', 0))
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        logging.info('SMTP Server stopped.')

if __name__ == '__main__':
    run()
