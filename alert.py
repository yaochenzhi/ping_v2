def alert(ip, status):
    print("{}: {}".format(ip, status))


if __name__ == "__main__":
    import pymysql

    with pymysql.connect(db='test') as cursor:
        cursor.execute("SELECT ip FROM alert")
        ips = [ item[0] for item in cursor ]
