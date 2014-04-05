#!/usr/bin/env python

"""
Written by Patman64.
"""

import numpy as np
import MySQLdb as mysql

# ALTER TABLE `creature_template` ADD `dmg_variance` FLOAT NOT NULL DEFAULT '1.0' AFTER `dmg_multiplier` ;
# ALTER TABLE `creature_template` ADD `armor_multiplier` FLOAT NOT NULL DEFAULT '1.0' AFTER `armor` ;

DB_INFO = {
        'db': 'udb',
      'host': 'localhost',
      'user': 'root',
    'passwd': ''
}

OUTPUT_FILE = 'output.sql'

def remove_a_sigfig(x):
    if type(x) == int:
        x = float(x)
    from math import modf
    if modf(x)[0] == 0.0:
        for i in range(1, len(str(x)) - 2):
            if x % 10**i != 0:
                return round(x / 10**i) * 10**i
        return x
    else:
        non_decimal = str(x).index('.')+1
        return round(x, len(str(x)) - non_decimal - 1)

if __name__ == '__main__':
    buff = ''
    def log(message):
        global buff
        buff += message + '\n'
    def flush_log(letter=None, write_out=True):
        global buff
        if write_out and letter:
            letter = letter.upper()
            import string
            if not letter in string.ascii_uppercase:
                letter = '#'
            with open('logs/{}.txt'.format(letter), 'a') as out:
                out.write(buff)
        buff = ''

    connection = mysql.connect(**DB_INFO)
    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT entry, minlevel, maxlevel, minhealth, maxhealth, minmana,
            maxmana, armor, mindmg, maxdmg FROM bestiary""")

        rows = [dict(entry=r[0], minlevel=r[1], maxlevel=r[2], minhealth=r[3],
            maxhealth=r[4], minmana=r[5], maxmana=r[6], armor=r[7],
            mindmg=r[8], maxdmg=r[9]) for r in cursor.fetchall()]

        for bestiary in rows:
            entry = bestiary['entry']
            log('=' * 79)

            cursor.execute("""
                SELECT name, minlevel, maxlevel, unit_class,
                baseattacktime, unk16, unk17, armor_multiplier,
                minhealth, maxhealth, minmana, maxmana
                FROM creature_template WHERE entry = %s""", (entry,))
            row = cursor.fetchone()

            if not row:
                log('ERROR: Creature could not be found! (Entry: {})'.format(entry))
                flush_log('#')
                continue

            real_name, min_level, max_level, unit_class,\
            attack_time, health_mult, mana_mult, armor_multiplier,\
            db_min_health, db_max_health, db_min_mana, db_max_mana = row
            attack_time /= 1000.0

            cursor.execute(
                "SELECT expansion FROM creature_template_expansion WHERE entry = %s",
                (entry,))
            expansion = cursor.fetchone()[0]

            if expansion == -1:
                log('\nERROR: Creature has expansion value -1. (Entry: {})'.format(entry))
                flush_log(real_name[0])
                continue
            else: real_expansion = expansion
            
            log('')
            log('DATABASE')
            log('  Name:      ' + str(real_name))
            log('  Entry:     ' + str(entry))
            log('  Expansion: ' + str(real_expansion))
            log('  Class:     ' + str(unit_class))
            log('  Min level: ' + str(min_level))
            log('  Max level: ' + str(max_level))
            log('')

            if unit_class == 0: unit_class = 1

            def binput(message, value):
                value = bestiary[value]
                log('  ' + message + str(value))
                return value

            log('BESTIARY')
            real_min_level  = binput('Min level: ' , 'minlevel')
            real_max_level  = binput('Max level: ' , 'maxlevel')

            log('')
            min_damage = binput('Min damage: ', 'mindmg')
            max_damage = binput('Max damage: ', 'maxdmg')

            cursor.execute("""
                SELECT BaseHealthExp{0}, BaseMana
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_min_level, unit_class))

            l_base_health, l_base_mana = cursor.fetchone()

            cursor.execute("""
                SELECT BaseHealthExp{0}, BaseMana
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_max_level, unit_class))

            h_base_health, h_base_mana = cursor.fetchone()

            min_health = round(l_base_health * health_mult)
            max_health = round(h_base_health * health_mult)

            min_mana = round(l_base_mana * mana_mult)
            max_mana = round(h_base_mana * mana_mult)

            log('')
            log('DATABASE')
            log('  Min health:  ' + str(min_health))
            log('  Max health:  ' + str(max_health))
            log('  Min mana:    ' + str(min_mana))
            log('  Max mana:    ' + str(max_mana))
            log('  Health mult: ' + str(health_mult))
            log('  Mana mult:   ' + str(mana_mult))
            log('')

            #if db_min_health != min_health or db_max_health != max_health or \
            #    db_min_mana != min_mana or db_max_mana != max_mana:
            #    log('********************************************')
            #    log('*  WARNING: Possible Health/Mana Mismatch  *')
            #    log('********************************************')
            #    log('')

            log('BESTIARY')
            real_min_health = binput('Min health: ', 'minhealth')
            real_max_health = binput('Max health: ', 'maxhealth')
            real_min_mana   = binput('Min mana: '  , 'minmana')
            real_max_mana   = binput('Max mana: '  , 'maxmana')
            log('')

            unk16 = unk17 = None

            def equal(a, b):
                """
                Returns True if a and b are within 1 unit of each other.
                This is considered close enough to be equal.
                """
                if abs(a - b) > 1.0: return False
                return True

            if not equal(real_min_health, min_health) or \
                not equal(real_max_health, max_health) or \
                not equal(real_min_mana, min_mana) or \
                not equal(real_max_mana, max_mana):
                suggestion = other_expansion = None

                cursor.execute("""
                    SELECT Class, BaseHealthExp{0}, BaseMana
                    FROM creature_template_classlevelstats
                    WHERE Level = %s""".format(real_expansion),
                    (real_min_level,))

                for t_unit_class, base_health, base_mana in cursor.fetchall():
                    c_min_health = base_health * health_mult
                    c_min_mana = base_mana * mana_mult

                    if abs(c_min_health - real_min_health) <= 4:
                        if abs(c_min_mana - real_min_mana) <= 4:
                            suggestion = t_unit_class
                            break

                # No suggestion, try the other expansion value.
                if not suggestion:
                    other_expansion = str(0 if real_expansion == 1 else 1)
                    cursor.execute("""
                        SELECT Class, BaseHealthExp{0}, BaseMana
                        FROM creature_template_classlevelstats
                        WHERE Level = %s""".format(other_expansion),
                        (real_min_level,))

                    for t_unit_class, base_health, base_mana in cursor.fetchall():
                        c_min_health = base_health * health_mult
                        c_min_mana = base_mana * mana_mult

                        if abs(c_min_health - real_min_health) <= 4:
                            if abs(c_min_mana - real_min_mana) <= 4:
                                suggestion = t_unit_class
                                break

                if not suggestion:
                    log('ERROR: Could not find proper class/expansion combination for NPC.')
                    flush_log(real_name[0])
                    continue

                real_unit_class = suggestion
                if other_expansion:
                    real_expansion, expansion = other_expansion, real_expansion
            else:
                real_unit_class = unit_class

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_min_level, real_unit_class))

            l_base_armor, l_base_damage, l_base_AP = cursor.fetchone()
            if l_base_armor == 0 or l_base_damage == 0 or l_base_AP == 0:
                log('ERROR: Missing level stats for level: {}, class: {}.'\
                    .format(real_min_level, real_unit_class))
                flush_log(real_name[0])
                continue

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_max_level, real_unit_class))

            h_base_armor, h_base_damage, h_base_AP = cursor.fetchone()
            if h_base_armor == 0 or h_base_damage == 0 or h_base_AP == 0:
                log('ERROR: Missing level stats for level: {}, class: {}.'\
                    .format(real_max_level, real_unit_class))
                flush_log(real_name[0])
                continue

            l_base_armor = float(l_base_armor)
            h_base_armor = float(h_base_armor)
            min_armor = round(l_base_armor * armor_multiplier)
            max_armor = round(h_base_armor * armor_multiplier)

            log('DATABASE')
            log('  Min armor: ' + str(min_armor))
            log('  Max armor: ' + str(max_armor))
            log('')

            log('BESTIARY')
            real_max_armor = binput('Max armor: ', 'armor')
            log('')

            if real_max_armor != max_armor:
                real_armor_multiplier = real_max_armor / h_base_armor

                # Reduce the accuracy of the multiplier.
                for i in range(len(str(real_armor_multiplier)) - 1):
                    last = real_armor_multiplier
                    real_armor_multiplier = remove_a_sigfig(real_armor_multiplier)

                    if abs(real_armor_multiplier * h_base_armor - real_max_armor) > 1.0:
                        real_armor_multiplier = last
                        break
            else:
                real_armor_multiplier = armor_multiplier

            if min_damage == 0:
                multiplier = 0.0
                variance = 1.0
            else:
                a = np.array([
                    [ l_base_damage * attack_time,       l_base_AP / 14.0 * attack_time ],
                    [ h_base_damage * attack_time * 1.5, h_base_AP / 14.0 * attack_time ]])

                # Try to find a working multiplier for variance = 1.
                base = np.dot(a, np.array([1, 1]))
                multiplier = min_damage / base[0]
                calculated_max = base[1] * multiplier
                
                if abs(calculated_max - max_damage) < 2:
                    variance = 1.0
                    multiplier = (min_damage + max_damage) / (base[0] + base[1])
                else: # Variance = 1 does not work.
                    #log('')
                    #log(a)
                    b = np.array([ min_damage, max_damage ])
                    #log('')
                    #log(b)
                    x = np.linalg.solve(a, b)
                    #log('')
                    #log(x)

                    multiplier = x[1]
                    variance = x[0] / multiplier

                    # Try rounding the variance to 2 decimal places.
                    base = np.dot(a, np.array([round(variance, 2), 1]))
                    calculated_max = base[1] * min_damage / base[0]

                    if abs(calculated_max - max_damage) < 2:
                        variance = round(variance, 2)
                        multiplier = (min_damage + max_damage) / (base[0] + base[1])
                    else: # Reduce as much as possible.
                        variance = reduce_accuracy(variance, False)
                        assert variance, "{} ({})".format(real_name, entry)
                
                def reduce_accuracy(var, is_multiplier):
                    var = remove_a_sigfig(var)
                    # No more sigfigs to remove!
                    if remove_a_sigfig(var) == var:
                        return var
                    #log('\nvar: ' + str(var))

                    if is_multiplier:
                        c_min_damage = (l_base_damage * 1.0 * variance + l_base_AP / 14.0) * attack_time * var
                        c_max_damage = (h_base_damage * 1.5 * variance + h_base_AP / 14.0) * attack_time * var
                    else:
                        c_min_damage = (l_base_damage * 1.0 * var + l_base_AP / 14.0) * attack_time * multiplier
                        c_max_damage = (h_base_damage * 1.5 * var + h_base_AP / 14.0) * attack_time * multiplier
                    
                    #log('c_min_damage: {}\nc_max_damage: {}'.format(c_min_damage, c_max_damage))
                    if abs(c_min_damage - min_damage) > 1.0: return None
                    if abs(c_max_damage - max_damage) > 1.0: return None

                    result = reduce_accuracy(var, is_multiplier)
                    if result: return result
                    else: return var

                multiplier = reduce_accuracy(multiplier, True)
                assert multiplier

            log('')
            log('NEW CALCULATED VALUES')
            log('  Multiplier: ' + str(multiplier))
            log('  Variance:   ' + str(variance))
            if real_armor_multiplier != armor_multiplier:
                log('  Armor multiplier: ' + str(real_armor_multiplier))
            if real_expansion != expansion:
                log('  Expansion:  ' + str(real_expansion))
            if real_unit_class != unit_class:
                log('  Class:      ' + str(real_unit_class))

            with open(OUTPUT_FILE, 'a') as out:
                out.write('-- {} ({})\n'.format(real_name, entry))

                if real_expansion != expansion:
                    out.write(
                        "UPDATE `creature_template_expansion` SET `expansion` = '{}' WHERE `entry` = '{}';\n"\
                        .format(real_expansion, entry))

                out.write('UPDATE `creature_template` SET ')

                def update_field(field, value, trailing_comma=True):
                    if trailing_comma:
                        out.write("`{}` = '{}', ".format(field, value))
                    else:
                        out.write("`{}` = '{}' ".format(field, value))

                if real_armor_multiplier != armor_multiplier:
                    update_field('armor_multiplier', real_armor_multiplier)

                if real_unit_class != unit_class:
                    update_field('unit_class', real_unit_class)

                if real_min_level != min_level:
                    update_field('minlevel', int(real_min_level))

                if real_max_level != max_level:
                    update_field('maxlevel', int(real_max_level))

                update_field('minhealth', int(real_min_health))
                update_field('maxhealth', int(real_max_health))

                update_field('minmana', int(real_min_mana))
                update_field('maxmana', int(real_max_mana))

                update_field('mindmg', int(min_damage))
                update_field('maxdmg', int(max_damage))

                update_field('dmg_multiplier', multiplier)
                update_field('dmg_variance', variance, trailing_comma=False)

                out.write("WHERE `entry` = '{}';\n\n".format(entry))

            # break
            flush_log(real_name[0], write_out=False)

        print 'All done!'

    finally: connection.close()