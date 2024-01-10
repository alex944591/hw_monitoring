from datetime import datetime
import asyncore
from smtpd import SMTPServer

class EmlServer(SMTPServer):
    no = 0

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        filename = '%s-%d.eml' % (datetime.now().strftime('%Y%m%d%H%M%S')+f'_{peer[0]}',
            self.no)

        print(filename)
        f = open(filename, 'wb')
        f.write(data)
        f.close()
        print('%s saved.' % filename)
        self.no += 1

def run():
    EmlServer(('0.0.0.0', 25), remoteaddr=('', 0))
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run()