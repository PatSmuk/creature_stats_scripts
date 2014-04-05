#!/usr/bin/env python

"""
Written by Patman64.
"""

import MySQLdb as mysql

DB_INFO = {
        'db': 'udb',
      'host': 'localhost',
      'user': 'root',
    'passwd': ''
}

OUTPUT_FILE = 'bestiary_armor.sql'

def main(cursor):
    # Attempt to find our place again if we crashed last time.
    try:
        with open('last_creature.txt', 'r') as last_creature_f:
            last_creature = last_creature_f.readline()
    except:
        last_creature = None

    cursor.execute("SELECT entry, name, minlevel, maxlevel, armor FROM bestiary WHERE minlevel != maxlevel ORDER BY name ASC;")
    for entry, name, minlevel, maxlevel, armor in cursor.fetchall():
        if last_creature:
            if name == last_creature: last_creature = None
            continue

        print ''
        print '{} (Entry: {})'.format(name, entry)
        print 'Level: {} - {}'.format(minlevel, maxlevel)
        print 'Avg armor: {}' .format(armor)
        armor = raw_input('Max armor: ')
        if armor == '': continue
        armor = int(armor)

        with open(OUTPUT_FILE, 'a') as out:
            out.write("UPDATE `bestiary` SET `armor` = '{}' WHERE `entry` = '{}';\n".format(armor, entry))

        with open('last_creature.txt', 'w') as out:
            out.write(name)


if __name__ == '__main__':
    connection = mysql.connect(**DB_INFO)
    try:
        cursor = connection.cursor()
        main(cursor)
    finally:
        connection.close()