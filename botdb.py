from mysql.connector import MySQLConnection, Error
import csv
import os


class BotDB:
    config = None
    conn = None
    cursor = None

    def __init__(self, config):
        self.config = config
        try:
            print('Connecting to MySQL...')
            self.conn = MySQLConnection(user=self.config.get('mysql', 'user'),
                                        password=self.config.get('mysql', 'password'),
                                        host=self.config.get('mysql', 'host'),
                                        database=self.config.get('mysql', 'database'))
            self.cursor = self.conn.cursor()
        except Error as error:
            print(error)

    def callproc(self, procname, args=[]):
        results = None
        try:
            if self.conn.is_connected():
                if len(args) == 0:
                    self.cursor.callproc(procname)
                else:
                    self.cursor.callproc(procname, args)

                self.conn.commit()  # do a commit
                for result in self.cursor.stored_results():
                    results = result.fetchall()  # save procedure results
            else:
                print('connection failed.')

            return results
        except Error as error:
            print(error)

    @staticmethod
    def savecsv(data, fname):
        try:
            os.remove(fname)
        except:
            pass
        try:
            # open file in write mode and hold object
            # create csv write object
            with open(fname, 'wt', newline="") as out:
                csv_out = csv.writer(out)
                for row in data:
                    csv_out.writerow(row)

        except Exception as e:
            print(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            print('connection closed.')
