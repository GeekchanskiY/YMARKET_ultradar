import ftplib
from VARS import ftp_login, ftp_url, ftp_password


def getfile(ftp_client, filename):
    ftp_client.retrbinary("RETR " + filename, open(filename, 'wb').write)


def main():
    ftp = ftplib.FTP(ftp_url)
    ftp.login(ftp_login, ftp_password)

    getfile(ftp, 'Base.xml')

    ftp.quit()


if __name__ == '__main__':
    main()
