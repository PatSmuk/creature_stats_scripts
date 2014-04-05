#!/usr/bin/env python

"""
Written by Patman64.
"""

import MySQLdb as mysql
from math import ceil, log10

DB_INFO = {
        'db': 'tbcdb',
      'host': 'localhost',
      'user': 'root',
    'passwd': ''
}

OUTPUT_FILE = 'damage_updates.sql'
ACCURACY = 1

MAX_LEVEL = 75
EXPANSIONS = [0, 1]

def main(cursor):
    print 'Loading creature stats...'
    cursor.execute("""
        SELECT Level, Class, BaseDamageExp0, BaseDamageExp1,
        BaseMeleeAttackPower, BaseRangedAttackPower
        FROM creature_template_classlevelstats""")

    stats = {}
    for row in cursor.fetchall():
        Level, Class = row[0], row[1]
        if not Class in stats: stats[Class] = {}
        stats[Class][Level] = dict(
            BaseDamageExp0=row[2],
            BaseDamageExp1=row[3],
            BaseMeleeAttackPower=row[4],
            BaseRangedAttackPower=row[5])

    print '\nGenerating damage stats...\n'
    cursor.execute("""
        SELECT Entry, Name, MinLevel, MaxLevel, UnitClass, Expansion,
        DamageMultiplier, DamageVariance,
        MinMeleeDmg, MaxMeleeDmg, MeleeBaseAttackTime
        FROM creature_template""")

    counters = {'unchecked': 0, 'defective': 0, 'updated': 0, 'unchanged': 0}
    creature_count = 0

    with open(OUTPUT_FILE, 'w') as f:
        for row in cursor.fetchall():
            creature_count += 1
            try:
                rv = generate_stats(f, stats, *row)
                counters[rv] += 1
            except:
                print 'Error while checking {} (Entry: {}):'.format(*row)
                raise

        if creature_count > 0:
            print 'Out of {0} creatures:'.format(creature_count)
            for k, v in counters.iteritems():
                print '    - {0} creatures were {1}.'.format(v, k)
        else:
            print 'No creatures in database!'

    print '\nFull report saved to: ' + OUTPUT_FILE

def make_multiplier_and_damage_gens(exp, l_stats, h_stats):
    """
    Return functions to generate damage and damage multipliers
      for expansion exp using base stats l_stats and h_stats.
    """
    dam_field = 'BaseDamageExp' + str(exp)

    def generate_damage(variance, multiplier, attacktime):
        ap_field = 'BaseMeleeAttackPower'
        l_ap = l_stats[ap_field]
        h_ap = h_stats[ap_field]
        l_b_damage = l_stats[dam_field]
        h_b_damage = h_stats[dam_field]

        l_damage = (l_b_damage * variance       + l_ap/14.0) * attacktime/1000.0 * multiplier
        h_damage = (h_b_damage * variance * 1.5 + h_ap/14.0) * attacktime/1000.0 * multiplier

        return l_damage, h_damage

    def generate_multipliers(l_damage, h_damage, attacktime):
        """
        Generate the proper multiplier and variance for a creature with
        minimum damage l_damage and maximum damage h_damage,
        using l_stats and h_stats for base damage and base AP.

        The formulae for damage multiplier and damage variance were determined
        using Maple, with the following steps (Maple input shown):

        Formulae for minimum and maximum damage:
        > Entered as shown.

          (1) (base_L * var + AP_L/14) * time/1000 * multiplier = min_damage

          (2) (base_H * var * 1.5 + AP_H/14) * time/1000 * multiplier = max_damage

        Re-arrange (2) to isolate multiplier:
        > solve((2), multiplier)

          (3) 14000 * max_damage / ((21 * base_H * var + AP_H) * time)

        Substitute (3) into (1) in place of multiplier:
        > subs(multiplier = (3), (1))

          (4) (14*(base_L*var+AP_L/14))*max_damage/(21*base_H*var+AP_H) = min_damage

        Now solve (4) for var:
        > solve((4), var)

          (5) -(0.1428571429*(AP_H*min_damage-AP_L*max_damage))/(3*base_H*min_damage-2*base_L*max_damage)

        Calculate variance using (5).
        Substitute this value into (2) to calculate the multiplier.
        """
        ap_field = 'BaseMeleeAttackPower'
        l_ap = l_stats[ap_field]
        h_ap = h_stats[ap_field]
        l_b_damage = l_stats[dam_field]
        h_b_damage = h_stats[dam_field]

        # Prevent division by zero.
        if 3 * h_b_damage * l_damage == 2 * l_b_damage * h_damage:
            l_damage += 0.5
            h_damage -= 0.5

        variance = -(0.1428571429*(h_ap*l_damage - l_ap*h_damage))\
                   /(3*h_b_damage*l_damage - 2*l_b_damage*h_damage)

        multiplier = 14000 * h_damage / ((21 * h_b_damage * variance + h_ap) * attacktime)

        return multiplier, variance
    return generate_damage, generate_multipliers

def generate_stats(
    out, stats, entry, name, l_level, h_level, unit_class, expansion,
    d_multiplier, d_variance, l_damage, h_damage, attacktime):

    # Skip creatures with expansion == -1 or unit class == 0.
    if expansion == -1 or unit_class == 0: return 'unchecked'

    try:
        # Check that min and max damage are set and not equal.
        assert l_damage != 0 and h_damage != 0,\
            'Min damage ({}) or max damage ({}) is zero!'.format(l_damage, h_damage)

        assert l_damage != h_damage,\
            'Min melee damage ({}) is the same as max damage!'.format(l_damage)

        # Make sure that the level and expansion values make sense.
        assert l_level >= 1,\
            'Min level {} is less than 1!'.format(l_level)

        assert l_level <= h_level,\
            'Min level {} is greater than max level {}!'.format(l_level, h_level)

        assert h_level <= MAX_LEVEL,\
            'Max level {} is greater than {}!'.format(h_level, MAX_LEVEL)

        assert expansion in EXPANSIONS,\
            'Expansion {} is not in {}!'.format(expansion, EXPANSIONS)

        assert attacktime != 0, 'Melee attack time is zero!'

        # Make sure stats are available for this combo.
        l_stats, h_stats = stats[unit_class][l_level], stats[unit_class][h_level]
        assert l_stats['BaseDamageExp' + str(expansion)] != 0,\
            'Missing base damage for exp {} class {} level {}!'.format(expansion, unit_class, l_level)

        assert h_stats['BaseDamageExp' + str(expansion)] != 0,\
            'Missing base damage for exp {} class {} level {}!'.format(expansion, unit_class, h_level)

    except AssertionError, e:
        print 'Failed assertion for {} (entry: {}):'.format(name, entry)
        print str(e) + '\n'
        return 'defective'

    def within_range(a, b):
        return abs(a - b) <= ACCURACY

    gen_damage, gen_multipliers = make_multiplier_and_damage_gens(expansion, l_stats, h_stats)

    # Does the creature need any changes?
    needs_update = False

    # First check the melee stats.
    # Generate a new multiplier and variance based on DB damage.
    multiplier, variance = gen_multipliers(l_damage, h_damage, attacktime)
    # Now calculate min and max damage using the old multiplier and variance.
    l_g_damage, h_g_damage = gen_damage(d_variance, d_multiplier, attacktime)

    # If these two values don't match, DB multiplier and variance needs changing.
    if not within_range(l_g_damage, l_damage): needs_update = True
    if not within_range(h_g_damage, h_damage): needs_update = True

    if needs_update:
        # Need more multiplier accuracy for higher damage values.
        accuracy = int(ceil(log10(h_damage)))

        out.write("-- {} ({})\n".format(name, entry))
        out.write("UPDATE creature_template SET\n")
        out.write("DamageMultiplier = {{:.{0}f}}, DamageVariance = {{:.{0}f}}\n".format(accuracy).format(multiplier, variance))
        out.write("WHERE entry = {};\n\n".format(entry))
        return 'updated'

    return 'unchanged'

if __name__ == '__main__':
    connection = mysql.connect(**DB_INFO)
    try:
        cursor = connection.cursor()
        main(cursor)
    finally:
        connection.close()