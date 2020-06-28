def constrain(val, lower, upper):
    if val > upper: return upper
    if val < lower: return lower

    return val


def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min