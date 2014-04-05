#!/usr/bin/env python

"""
Generates dmg_variance and dmg_multiplier fields for creatures
based on Bestiary data entered by the user and pre-existing fields in the DB.

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
    connection = mysql.connect(**DB_INFO)
    try:
        cursor = connection.cursor()

        while True:
            print ''
            name = raw_input('Creature name: ')
            if name == '': break
            cursor.execute("""
                SELECT entry, name, minlevel, maxlevel, unit_class,
                baseattacktime, unk16, unk17, armor_multiplier,
                minhealth, maxhealth, minmana, maxmana
                FROM creature_template WHERE name = %s""", (name,))
            row = cursor.fetchone()

            if not row:
                print 'Creature could not be found!'
                continue

            entry, real_name, min_level, max_level, unit_class,\
            attack_time, health_mult, mana_mult, armor_multiplier,\
            db_min_health, db_max_health, db_min_mana, db_max_mana = row
            attack_time /= 1000.0

            cursor.execute(
                "SELECT expansion FROM creature_template_expansion WHERE entry = %s",
                (entry,))
            expansion = cursor.fetchone()[0]

            if expansion == -1: real_expansion = int(raw_input('Expansion: '))
            else: real_expansion = expansion
            
            print ''
            print 'DATABASE'
            print '  Entry:     ' + str(entry)
            print '  Expansion: ' + str(real_expansion)
            print '  Class:     ' + str(unit_class)
            print '  Min level: ' + str(min_level)
            print '  Max level: ' + str(max_level)
            print ''

            def opt_input(message, default, corrected=None, original=None):
                data = raw_input(message)
                if data == '':
                    if corrected == original: return default
                    else: return corrected
                return int(data)

            print 'BESTIARY'
            real_min_level  = opt_input('  Min level: ' , min_level)
            real_max_level  = opt_input('  Max level: ' , max_level, real_min_level, min_level)

            print ''
            min_damage = float( raw_input('  Min damage: ') )
            max_damage = float( raw_input('  Max damage: ') )

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

            print ''
            print 'DATABASE'
            print '  Min health:  ' + str(min_health)
            print '  Max health:  ' + str(max_health)
            print '  Min mana:    ' + str(min_mana)
            print '  Max mana:    ' + str(max_mana)
            print '  Health mult: ' + str(health_mult)
            print '  Mana mult:   ' + str(mana_mult)
            print ''

            if db_min_health != min_health or db_max_health != max_health or \
                db_min_mana != min_mana or db_max_mana != max_mana:
                print '********************************************'
                print '*  WARNING: Possible Health/Mana Mismatch  *'
                print '********************************************'
                print ''

            print 'BESTIARY'
            real_min_health = opt_input('  Min health: ', min_health)
            real_max_health = opt_input('  Max health: ', max_health, real_min_health, min_health)
            real_min_mana   = opt_input('  Min mana: '  , min_mana)
            real_max_mana   = opt_input('  Max mana: '  , max_mana, real_min_mana, min_mana)
            print ''

            unk16 = unk17 = None

            if real_min_health != min_health or real_max_health != max_health \
            or real_min_mana != min_mana or real_max_mana != max_mana:
                suggestion = None

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

                real_unit_class = opt_input('New unit class ({}): '\
                    .format('suggestion: ' + str(suggestion) if suggestion else 'no suggestion'),
                    unit_class)
            else:
                real_unit_class = unit_class

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_min_level, real_unit_class))

            l_base_armor, l_base_damage, l_base_AP = cursor.fetchone()

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(real_expansion), (real_max_level, real_unit_class))

            h_base_armor, h_base_damage, h_base_AP = cursor.fetchone()

            l_base_armor = float(l_base_armor)
            h_base_armor = float(h_base_armor)
            min_armor = round(l_base_armor * armor_multiplier)
            max_armor = round(h_base_armor * armor_multiplier)

            print 'DATABASE'
            print '  Min armor: ' + str(min_armor)
            print '  Max armor: ' + str(max_armor)
            print ''

            print 'BESTIARY'
            real_min_armor = opt_input('  Min armor: ', min_armor)
            real_max_armor = opt_input('  Max armor: ', max_armor)
            print ''

            if real_min_armor != min_armor or real_max_armor != max_armor:
                real_armor_multiplier = real_min_armor / l_base_armor

                # Reduce the accuracy of the multiplier.
                for i in range(len(str(real_armor_multiplier)) - 1):
                    last = real_armor_multiplier
                    real_armor_multiplier = remove_a_sigfig(real_armor_multiplier)

                    if abs(real_armor_multiplier * l_base_armor - real_min_armor) > 1.0:
                        real_armor_multiplier = last
                        break
            else:
                real_armor_multiplier = armor_multiplier

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
                print ''
                print a
                b = np.array([ min_damage, max_damage ])
                print ''
                print b
                x = np.linalg.solve(a, b)
                print ''
                print x

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
                    assert variance
            
            def reduce_accuracy(var, is_multiplier):
                var = remove_a_sigfig(var)
                # No more sigfigs to remove!
                if remove_a_sigfig(var) == var:
                    return var
                #print '\nvar: ' + str(var)

                if is_multiplier:
                    c_min_damage = (l_base_damage * 1.0 * variance + l_base_AP / 14.0) * attack_time * var
                    c_max_damage = (h_base_damage * 1.5 * variance + h_base_AP / 14.0) * attack_time * var
                else:
                    c_min_damage = (l_base_damage * 1.0 * var + l_base_AP / 14.0) * attack_time * multiplier
                    c_max_damage = (h_base_damage * 1.5 * var + h_base_AP / 14.0) * attack_time * multiplier
                
                #print 'c_min_damage: {}\nc_max_damage: {}'.format(c_min_damage, c_max_damage)
                if abs(c_min_damage - min_damage) > 1.0: return None
                if abs(c_max_damage - max_damage) > 1.0: return None

                result = reduce_accuracy(var, is_multiplier)
                if result: return result
                else: return var

            multiplier = reduce_accuracy(multiplier, True)
            assert multiplier

            print ''
            print 'NEW CALCULATED VALUES'
            print '  Multiplier: ' + str(multiplier)
            print '  Variance:   ' + str(variance)
            if real_armor_multiplier != armor_multiplier:
                print '  Armor multiplier: ' + str(real_armor_multiplier)

            with open(OUTPUT_FILE, 'a') as out:
                out.write('-- {} ({})\n'.format(real_name, entry))

                if real_expansion != expansion:
                    out.write(
                        "UPDATE `creature_template_expansion` SET `expansion` = '%s' WHERE `entry` = '%s';\n",
                        (real_expansion, entry))

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

                print ''
                print 'RECORDED SUCCESSFULLY'
                print ('=' * 79)

    finally: connection.close()