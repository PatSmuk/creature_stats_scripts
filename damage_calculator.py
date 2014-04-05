#!/usr/bin/env python

import numpy as np

if __name__ == '__main__':
    def get_float(message):
        value = raw_input(message)
        if value == '': return None
        return float(value)

    l_base_damage = get_float('Min base damage: ')
    l_base_ap     = get_float('Min base AP: ')
    h_base_damage = get_float('Max base damage: ') or l_base_damage
    h_base_ap     = get_float('Max base AP: ') or l_base_ap
    time          = get_float('Attack time (msecs): ') / 1000.0
    min_damage    = get_float('Min. damage: ')
    max_damage    = get_float('Max. damage: ')

    a = np.array([
        [l_base_damage * time,       l_base_ap / 14 * time],
        [h_base_damage * time * 1.5, h_base_ap / 14 * time]])
    b = np.array([min_damage, max_damage])
    x = np.linalg.solve(a, b)

    multiplier = x[1]
    variance = x[0] #/ multiplier

    print ''
    print 'Multiplier: ' + str(multiplier)
    print 'Variance: '   + str(variance)