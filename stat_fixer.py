#!/usr/bin/env python

"""
Generates Damage Variance and Damage Multiplier fields for creatures
based on desired Min/Max Damage Values For an NPC.

Written by Patman64 / X-Savior.
"""

import numpy as np
import MySQLdb as mysql

DB_INFO = {
        'db': 'tbc_database',
      'host': '127.0.0.1',
      'user': 'root',
    'passwd': '********'
}

OUTPUT_FILE = '243_Manual_Damage_Calculator_Script.sql'

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
            entry = raw_input('Creature entry: ')

            cursor.execute("""
                SELECT entry, name, minlevel, maxlevel, unitclass, expansion,
                meleebaseattacktime, rangedbaseattacktime, healthmultiplier, manamultiplier, armormultiplier,
                damagemultiplier, damagevariance, minlevelhealth, maxlevelhealth, minlevelmana, maxlevelmana, minmeleedmg, maxmeleedmg
                FROM creature_template WHERE entry = %s""", (entry,))
            row = cursor.fetchone()

            if not row:
                print 'Creature entry could not be found!'

                print ''
                name = raw_input('Creature name: ')
                if name == '': continue
                cursor.execute("""
                    SELECT entry, name, minlevel, maxlevel, unitclass, expansion,
                    meleebaseattacktime, rangedbaseattacktime, healthmultiplier, manamultiplier, armormultiplier,
                    damagemultiplier, damagevariance, minlevelhealth, maxlevelhealth, minlevelmana, maxlevelmana, minmeleedmg, maxmeleedmg
                    FROM creature_template WHERE name = %s""", (name,))
                row = cursor.fetchone()

                if not row:
                    print 'Creature could not be found!'
                    continue

            entry, real_name, min_level, max_level, unit_class, expansion,\
            attack_time, ranged_attack_time, health_mult, mana_mult, armor_multiplier,\
            damage_multiplier, damage_variance, db_min_health, db_max_health, db_min_mana, db_max_mana, db_minmeleedmg, db_maxmeleedmg = row
            attack_time /= 1000.0
            ranged_attack_time /= 1000.0

            print ''
            print '========================'
            print 'CURRENT DATABASE VALUES:'
            print '========================'
            print '  Entry:           ' + str(entry)
            print '  Name:            ' + str(real_name)
            print '  Expansion:       ' + str(expansion)
            print '  Unit Class:      ' + str(unit_class)
            print '  Min Level:       ' + str(min_level)
            print '  Max Level:       ' + str(max_level)

            cursor.execute("""
                SELECT BaseHealthExp{0}, BaseMana
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(expansion), (min_level, unit_class))

            l_base_health, l_base_mana = cursor.fetchone()

            cursor.execute("""
                SELECT BaseHealthExp{0}, BaseMana
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(expansion), (max_level, unit_class))

            h_base_health, h_base_mana = cursor.fetchone()

            min_health = round(l_base_health * health_mult)
            max_health = round(h_base_health * health_mult)

            min_mana = round(l_base_mana * mana_mult)
            max_mana = round(h_base_mana * mana_mult)

            print '  Health Multi     ' + str(health_mult)
            print '  Min Health:      ' + str(min_health)
            print '  Max Health:      ' + str(max_health)
            print '  Mana Multi:      ' + str(mana_mult)
            print '  Min Mana:        ' + str(min_mana)
            print '  Max Mana:        ' + str(max_mana)

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower, BaseRangedAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(expansion), (min_level, unit_class))

            l_base_armor, l_base_damage, l_base_AP, l_base_ranged_AP = cursor.fetchone()

            cursor.execute("""
                SELECT BaseArmor, BaseDamageExp{0}, BaseMeleeAttackPower, BaseRangedAttackPower
                FROM creature_template_classlevelstats
                WHERE Level = %s AND Class = %s"""\
                .format(expansion), (max_level, unit_class))

            h_base_armor, h_base_damage, h_base_AP, h_base_ranged_AP = cursor.fetchone()

            l_base_armor = float(l_base_armor)
            h_base_armor = float(h_base_armor)
            min_armor = round(l_base_armor * armor_multiplier)
            max_armor = round(h_base_armor * armor_multiplier)

            print '  Min Armor:       ' + str(min_armor)
            print '  Max Armor:       ' + str(max_armor)
            print '  ------------------------'
            print '  Min Melee Dmg:   ' + str(db_minmeleedmg)
            print '  Max Melee Dmg:   ' + str(db_maxmeleedmg)
            print '  Dmg Multi:       ' + str(damage_multiplier)
            print '  Dmg Variance:    ' + str(damage_variance)
            print '  ------------------------'
            print ''

            a = np.array([
                [ l_base_damage * attack_time,       l_base_AP / 14.0 * attack_time ],
                [ h_base_damage * attack_time * 1.5, h_base_AP / 14.0 * attack_time ]])

            # Try to find a working multiplier for variance = 1.
            base = np.dot(a, np.array([1, 1]))
            multiplier = db_minmeleedmg / base[0]
            calculated_max = base[1] * multiplier
            
            if abs(calculated_max - db_maxmeleedmg) < 2:
                variance = 1.0
                multiplier = (db_minmeleedmg + db_maxmeleedmg) / (base[0] + base[1])
            else: # Variance = 1 does not work.
                print ''
                print a
                b = np.array([ db_minmeleedmg, db_maxmeleedmg ])
                print ''
                print b
                x = np.linalg.solve(a, b)
                print ''
                print x

                multiplier = x[1]
                variance = x[0] / multiplier

                # Try rounding the variance to 2 decimal places.
                base = np.dot(a, np.array([round(variance, 2), 1]))
                calculated_max = base[1] * db_minmeleedmg / base[0]

                if abs(calculated_max - db_maxmeleedmg) < 2:
                    variance = round(variance, 2)
                    multiplier = (db_minmeleedmg + db_maxmeleedmg) / (base[0] + base[1])
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
                    c_db_minmeleedmg = (l_base_damage * 1.0 * variance + l_base_AP / 14.0) * attack_time * var
                    c_db_maxmeleedmg = (h_base_damage * 1.5 * variance + h_base_AP / 14.0) * attack_time * var
                else:
                    c_db_minmeleedmg = (l_base_damage * 1.0 * var + l_base_AP / 14.0) * attack_time * multiplier
                    c_db_maxmeleedmg = (h_base_damage * 1.5 * var + h_base_AP / 14.0) * attack_time * multiplier
                
                #print 'c_db_minmeleedmg: {}\nc_db_maxmeleedmg: {}'.format(c_db_minmeleedmg, c_db_maxmeleedmg)
                if abs(c_db_minmeleedmg - db_minmeleedmg) > 1.0: return None
                if abs(c_db_maxmeleedmg - db_maxmeleedmg) > 1.0: return None

                result = reduce_accuracy(var, is_multiplier)
                if result: return result
                else: return var

            multiplier = reduce_accuracy(multiplier, True)
            assert multiplier

            print '==================================================='
            print 'CALCULATED VALUES BASED ON EXISTING DB DAMAGE DATA:'
            print '==================================================='
            print '  Damage Multiplier: ' + str(multiplier)
            print '  Damage Variance:   ' + str(variance)
            print ''

            def opt_input(message, default, corrected=None, original=None):
                data = raw_input(message)
                if data == '':
                    if corrected == original: return default
                    else: return corrected
                return int(data)

            while True:
                print '=================================='
                print 'NEW DESIRED MIN/MAX DAMAGE VALUES:'
                print '=================================='
                min_damage = raw_input('  Min Melee Damage: ')
                max_damage = raw_input('  Max Melee Damage: ')

                if min_damage == '' or max_damage == '':
                    print ''
                    print '============================'
                    print 'NEW DESIRED MULT/VAR VALUES:'
                    print '============================'
                    multiplier = float(raw_input('  Multiplier: '))
                    variance = float(raw_input('  Variance: '))

                    min_damage = ((l_base_damage * variance      ) + (l_base_AP / 14.0)) * attack_time * multiplier
                    max_damage = ((l_base_damage * variance * 1.5) + (l_base_AP / 14.0)) * attack_time * multiplier

                else:
                    min_damage = float(min_damage)
                    max_damage = float(max_damage)

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
                        b = np.array([ min_damage, max_damage ])
                        x = np.linalg.solve(a, b)

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

                min_ranged_damage = (l_base_damage * 1.0 * variance + l_base_ranged_AP / 14.0) * ranged_attack_time * multiplier
                max_ranged_damage = (h_base_damage * 1.5 * variance + h_base_ranged_AP / 14.0) * ranged_attack_time * multiplier
                
                print ''
                print '============================================'
                print 'NEW CALCULATED DATABASE VALUES DUMPED TO SQL'
                print '============================================'
                print '  Min Melee Dmg:     ' + str(min_damage)
                print '  Max Melee Dmg:     ' + str(max_damage)
                print '  Min Ranged Dmg:    ' + str(min_ranged_damage)
                print '  Max Ranged Dmg:    ' + str(max_ranged_damage)
                print '  Damage Multiplier: ' + str(multiplier)
                print '  Damage Variance:   ' + str(variance)

                print ''
                answer = ''

                while answer != 'N' and answer != 'Y':
                    answer = raw_input('  Is this acceptable? (Y/N): ').upper()

                    if answer != 'N' and answer != 'Y':
                        print ''
                        print 'Please enter Y or N.'

                if answer == 'Y':
                    break

            with open(OUTPUT_FILE, 'a') as out:
                out.write('-- {} ({})\n'.format(real_name, entry))

                out.write('UPDATE `creature_template` SET ')

                def update_field(field, value, trailing_comma=True):
                    if trailing_comma:
                        out.write("`{}` = '{}', ".format(field, value))
                    else:
                        out.write("`{}` = '{}' ".format(field, value))

                update_field('MinMeleeDmg', int(ceil(min_damage)))
                update_field('MaxMeleeDmg', int(ceil(max_damage)))

                update_field('MinRangedDmg', int(ceil(min_ranged_damage)))
                update_field('MaxRangedDmg', int(ceil(max_ranged_damage)))

                update_field('DamageMultiplier', multiplier)
                update_field('DamageVariance', variance, trailing_comma=False)

                out.write("WHERE `entry` = '{}';\n\n".format(entry))

                print ''
                print 'RECORDED SUCCESSFULLY'
                print ('=' * 79)

    finally: connection.close()
