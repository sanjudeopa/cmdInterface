#!/usr/bin/env python3

# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=too-many-statements
# pylint: disable=line-too-long
# pylint: disable=redefined-outer-name

import collections

class Field:
    def __init__(self, name, high_bit, low_bit = None, to_string = None):
        self.name = name
        self.high_bit = high_bit
        if low_bit is None:
            low_bit = high_bit
        self.low_bit = low_bit
        self.to_string = to_string

    def __str__(self):
        if self.high_bit == self.low_bit:
            return '{0} {1}'.format(self.low_bit, self.high_bit)
        else:
            return '{0} {1}:{2}'.format(self.high_bit, self.low_bit, self.name)

class FieldValue:
    def __init__(self, field, value, description = None):
        self.field = field
        self.name = field.name if field else None
        self.value = value
        self.description = description

    @classmethod
    def from_name_and_value(cls, name, value, description = None):
        ret = FieldValue(None, value, description)
        ret.name = name
        return ret

    def __str__(self):
        return '{0}={1}'.format(self.name, self.value)

                                                                              # armv8-pseudocode revision
MORELLO_ALPHA1='morello-alpha1'                                               # 558ebd4b3dc5c071272c37e5ecb6835f95a4b2f2
MORELLO_BETA0='morello-beta0'                                                 # 1cd63969f74bb357cb62c3c4ae3d2f2876f2ffd3
MORELLO_BETA0_UPDATE='morello-beta0-arran-596'                                # f457d6fe0847757a573a28b2df41fc8b99fd3b82
MORELLO_BETA0_FIXED_CHERI_CONCENTRATE='morello-beta0-fixed-cheri-concentrate' # 7b72a3aad14ac0c143f914574efec01e5d2fedd4
MORELLO_BETA1='morello-beta1'                                                 # b3668e86be5c1926e6d6efd6c3a3981b35a5a674
MORELLO_BETA1_ARRAN_822='morello-beta1-arran-822'                             # 6434eca83f073c3f6cc7139763f61f475e24365c
DEFAULT_SPEC_VERSION=MORELLO_BETA1_ARRAN_822

MORELLO_SPEC_VERSIONS = [MORELLO_ALPHA1,
                         MORELLO_BETA0,
                         MORELLO_BETA0_UPDATE,
                         MORELLO_BETA0_FIXED_CHERI_CONCENTRATE,
                         MORELLO_BETA1,
                         MORELLO_BETA1_ARRAN_822]

MORELLO_ALPHA1_PERMISSIONS = [ Field('Load', 17),
                               Field('Store', 16),
                               Field('Execute', 15),
                               Field('LoadCap', 14),
                               Field('StoreCap', 13),
                               Field('StoreLocalCap', 12),
                               Field('Seal', 11),
                               Field('Unseal', 10),
                               Field('System', 9),
                               Field('BranchUnseal', 8),
                               Field('CompartmentID', 7),
                               Field('MutableLoad', 6),
                               Field('User', 5, 2),
                               Field('Global', 1),
                               Field('Executive', 0) ]
MORELLO_ALPHA1_OBJECT_TYPES = { 1: 'RB',
                                2: 'LPB',
                                3: 'LB' }
MORELLO_ALPHA1_FIELDS = [ Field('Tag', 128),
                          Field('Permissions', 127, 110, lambda x: permissions_to_str(x, MORELLO_ALPHA1_PERMISSIONS)),
                          Field('ObjectType',  109, 95,  lambda x: object_type_to_str(x, MORELLO_ALPHA1_OBJECT_TYPES)),
                          Field('Bounds[86:56]', 94, 64),
                          Field('Flags', 63, 56),
                          Field('Bounds[55:0]', 55, 0),
                          Field('Value', 63, 0) ]

# The only difference between alpha 1 and beta 0 is the Executive and Global bits are swapped.
MORELLO_BETA0_PERMISSIONS = [ Field('Load', 17),
                              Field('Store', 16),
                              Field('Execute', 15),
                              Field('LoadCap', 14),
                              Field('StoreCap', 13),
                              Field('StoreLocalCap', 12),
                              Field('Seal', 11),
                              Field('Unseal', 10),
                              Field('System', 9),
                              Field('BranchUnseal', 8),
                              Field('CompartmentID', 7),
                              Field('MutableLoad', 6),
                              Field('User', 5, 2),
                              Field('Executive', 1),
                              Field('Global', 0) ]
MORELLO_BETA0_FIELDS = [ Field('Tag', 128),
                          Field('Permissions', 127, 110, lambda x: permissions_to_str(x, MORELLO_BETA0_PERMISSIONS)),
                          Field('ObjectType',  109, 95,  lambda x: object_type_to_str(x, MORELLO_ALPHA1_OBJECT_TYPES)),
                          Field('Bounds[86:56]', 94, 64),
                          Field('Flags', 63, 56),
                          Field('Bounds[55:0]', 55, 0),
                          Field('Value', 63, 0) ]

MORELLO_BETA0_UPDATE_FIELDS = [ Field('Tag', 128),
                                Field('Permissions', 127, 110, lambda x: permissions_to_str(x, MORELLO_BETA0_PERMISSIONS)),
                                Field('ObjectType',  109, 95,  lambda x: object_type_to_str(x, MORELLO_ALPHA1_OBJECT_TYPES)),
                                Field('IE', 94),
                                Field('Limit', 93, 80),
                                Field('Base', 79, 64),
                                Field('Flags', 63, 56),
                                Field('Bounds[55:0]', 55, 0),
                                Field('Value', 63, 0) ]

MORELLO_BETA1_FIELDS = MORELLO_BETA0_UPDATE_FIELDS
MORELLO_BETA1_ARRAN_822_FIELDS = MORELLO_BETA0_UPDATE_FIELDS

MORELLO_SPEC_VERSION_TO_FIELDS = {
    MORELLO_ALPHA1: MORELLO_ALPHA1_FIELDS,
    MORELLO_BETA0:  MORELLO_BETA0_FIELDS,
    MORELLO_BETA0_UPDATE: MORELLO_BETA0_UPDATE_FIELDS,
    MORELLO_BETA0_FIXED_CHERI_CONCENTRATE: MORELLO_BETA0_UPDATE_FIELDS,
    MORELLO_BETA1: MORELLO_BETA1_FIELDS,
    MORELLO_BETA1_ARRAN_822: MORELLO_BETA1_ARRAN_822_FIELDS
}

_MORELLO_ALPHA1_CAP_IE_BIT = 90
_MORELLO_ALPHA1_CAP_LIMIT_EXP_HI_BIT = 80
_MORELLO_ALPHA1_CAP_LIMIT_HI_BIT = 89
_MORELLO_ALPHA1_CAP_LIMIT_LO_BIT = 78
_MORELLO_ALPHA1_CAP_BASE_EXP_HI_BIT = 66
_MORELLO_ALPHA1_CAP_BASE_HI_BIT = 77
_MORELLO_ALPHA1_CAP_BASE_LO_BIT = 64
_MORELLO_ALPHA1_CAP_VALUE_HI_BIT = 63
_MORELLO_ALPHA1_CAP_VALUE_LO_BIT = 0
_MORELLO_ALPHA1_CAP_VALUE_FOR_BOUND_HI_BIT = 55
_MORELLO_ALPHA1_CAP_MW = _MORELLO_ALPHA1_CAP_BASE_HI_BIT - _MORELLO_ALPHA1_CAP_BASE_LO_BIT + 1
_MORELLO_ALPHA1_CAP_LIMIT_NUM_BITS = _MORELLO_ALPHA1_CAP_LIMIT_HI_BIT - _MORELLO_ALPHA1_CAP_LIMIT_LO_BIT + 1
_MORELLO_ALPHA1_CAP_VALUE_FOR_BOUND_NUM_BITS = _MORELLO_ALPHA1_CAP_VALUE_FOR_BOUND_HI_BIT - _MORELLO_ALPHA1_CAP_VALUE_LO_BIT + 1
_MORELLO_ALPHA1_CAP_VALUE_NUM_BITS = _MORELLO_ALPHA1_CAP_VALUE_HI_BIT - _MORELLO_ALPHA1_CAP_VALUE_LO_BIT + 1

_MORELLO_BETA0_UPDATE_CAP_IE_BIT = 94
_MORELLO_BETA0_UPDATE_CAP_LIMIT_HI_BIT = 93
_MORELLO_BETA0_UPDATE_CAP_LIMIT_EXP_HI_BIT = 82
_MORELLO_BETA0_UPDATE_CAP_LIMIT_LO_BIT = 80
_MORELLO_BETA0_UPDATE_CAP_BASE_HI_BIT = 79
_MORELLO_BETA0_UPDATE_CAP_BASE_EXP_HI_BIT = 66
_MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT = 64
_MORELLO_BETA0_UPDATE_CAP_VALUE_HI_BIT = 63
_MORELLO_BETA0_UPDATE_CAP_VALUE_LO_BIT = 0
_MORELLO_BETA0_UPDATE_CAP_VALUE_FOR_BOUND_HI_BIT = 55
_MORELLO_BETA0_UPDATE_CAP_MW = _MORELLO_BETA0_UPDATE_CAP_BASE_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT + 1
_MORELLO_BETA0_UPDATE_CAP_LIMIT_NUM_BITS = _MORELLO_BETA0_UPDATE_CAP_LIMIT_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_LIMIT_LO_BIT + 1
_MORELLO_BETA0_UPDATE_CAP_VALUE_FOR_BOUND_NUM_BITS = _MORELLO_BETA0_UPDATE_CAP_VALUE_FOR_BOUND_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_VALUE_LO_BIT + 1
_MORELLO_BETA0_UPDATE_CAP_VALUE_NUM_BITS = _MORELLO_BETA0_UPDATE_CAP_VALUE_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_VALUE_LO_BIT + 1

_MORELLO_BETA0_FIXED_CAP_IE_BIT                 = 94
_MORELLO_BETA0_FIXED_CAP_LIMIT_HI_BIT           = 93
_MORELLO_BETA0_FIXED_CAP_LIMIT_MANTISSA_LO_BIT  = 83
_MORELLO_BETA0_FIXED_CAP_LIMIT_EXP_HI_BIT       = 82
_MORELLO_BETA0_FIXED_CAP_LIMIT_LO_BIT           = 80
_MORELLO_BETA0_FIXED_CAP_BASE_HI_BIT            = 79
_MORELLO_BETA0_FIXED_CAP_BASE_MANTISSA_LO_BIT   = 67
_MORELLO_BETA0_FIXED_CAP_BASE_EXP_HI_BIT        = 66
_MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT            = 64
_MORELLO_BETA0_FIXED_CAP_VALUE_HI_BIT           = 63
_MORELLO_BETA0_FIXED_CAP_VALUE_LO_BIT           = 0
_MORELLO_BETA0_FIXED_CAP_VALUE_FOR_BOUND_HI_BIT = 55
_MORELLO_BETA0_FIXED_CAP_FLAGS_LO_BIT           = 56
_MORELLO_BETA0_FIXED_CAP_FLAGS_HI_BIT           = 63
_MORELLO_BETA0_FIXED_CAP_VALUE_NUM_BITS = _MORELLO_BETA0_FIXED_CAP_VALUE_HI_BIT-_MORELLO_BETA0_FIXED_CAP_VALUE_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_VALUE_FOR_BOUND_NUM_BITS = _MORELLO_BETA0_FIXED_CAP_VALUE_FOR_BOUND_HI_BIT-_MORELLO_BETA0_FIXED_CAP_VALUE_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_BASE_MANTISSA_NUM_BITS = _MORELLO_BETA0_FIXED_CAP_BASE_HI_BIT-_MORELLO_BETA0_FIXED_CAP_BASE_MANTISSA_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_LIMIT_NUM_BITS = _MORELLO_BETA0_FIXED_CAP_LIMIT_HI_BIT-_MORELLO_BETA0_FIXED_CAP_LIMIT_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_LIMIT_MANTISSA_NUM_BITS = _MORELLO_BETA0_FIXED_CAP_LIMIT_HI_BIT-_MORELLO_BETA0_FIXED_CAP_LIMIT_MANTISSA_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_MW = _MORELLO_BETA0_FIXED_CAP_BASE_HI_BIT-_MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT+1
_MORELLO_BETA0_FIXED_CAP_MAX_EXPONENT = _MORELLO_BETA0_FIXED_CAP_VALUE_NUM_BITS-_MORELLO_BETA0_FIXED_CAP_MW+2

_MORELLO_BETA1_CAP_IE_BIT                 = 94
_MORELLO_BETA1_CAP_LIMIT_HI_BIT           = 93
_MORELLO_BETA1_CAP_LIMIT_MANTISSA_LO_BIT  = 83
_MORELLO_BETA1_CAP_LIMIT_EXP_HI_BIT       = 82
_MORELLO_BETA1_CAP_LIMIT_LO_BIT           = 80
_MORELLO_BETA1_CAP_BASE_HI_BIT            = 79
_MORELLO_BETA1_CAP_BASE_MANTISSA_LO_BIT   = 67
_MORELLO_BETA1_CAP_BASE_EXP_HI_BIT        = 66
_MORELLO_BETA1_CAP_BASE_LO_BIT            = 64
_MORELLO_BETA1_CAP_VALUE_HI_BIT           = 63
_MORELLO_BETA1_CAP_VALUE_LO_BIT           = 0
_MORELLO_BETA1_CAP_VALUE_FOR_BOUND_HI_BIT = 55
_MORELLO_BETA1_CAP_FLAGS_LO_BIT           = 56
_MORELLO_BETA1_CAP_FLAGS_HI_BIT           = 63
_MORELLO_BETA1_CAP_VALUE_NUM_BITS = _MORELLO_BETA1_CAP_VALUE_HI_BIT-_MORELLO_BETA1_CAP_VALUE_LO_BIT+1
_MORELLO_BETA1_CAP_VALUE_FOR_BOUND_NUM_BITS = _MORELLO_BETA1_CAP_VALUE_FOR_BOUND_HI_BIT-_MORELLO_BETA1_CAP_VALUE_LO_BIT+1
_MORELLO_BETA1_CAP_BASE_MANTISSA_NUM_BITS = _MORELLO_BETA1_CAP_BASE_HI_BIT-_MORELLO_BETA1_CAP_BASE_MANTISSA_LO_BIT+1
_MORELLO_BETA1_CAP_LIMIT_NUM_BITS = _MORELLO_BETA1_CAP_LIMIT_HI_BIT-_MORELLO_BETA1_CAP_LIMIT_LO_BIT+1
_MORELLO_BETA1_CAP_LIMIT_MANTISSA_NUM_BITS = _MORELLO_BETA1_CAP_LIMIT_HI_BIT-_MORELLO_BETA1_CAP_LIMIT_MANTISSA_LO_BIT+1
_MORELLO_BETA1_CAP_MW = _MORELLO_BETA1_CAP_BASE_HI_BIT-_MORELLO_BETA1_CAP_BASE_LO_BIT+1
_MORELLO_BETA1_CAP_MAX_EXPONENT = _MORELLO_BETA1_CAP_VALUE_NUM_BITS-_MORELLO_BETA1_CAP_MW+2

_MORELLO_BETA1_ARRAN_822_CAP_MAX_ENCODEABLE_EXPONENT = 63
_MORELLO_BETA1_ARRAN_822_CAP_BOUND_MIN               = 0
_MORELLO_BETA1_ARRAN_822_CAP_BOUND_MAX               = 1<<_MORELLO_BETA1_CAP_VALUE_NUM_BITS

def _get_bit(x, n):
    return (x >> n) & 1

def _get_slice_hl(x, high, low):
    return (x >> low) & ((1 << (high - low + 1)) - 1)

def _get_slice_w(x, low, width):
    return (x >> low) & ((1 << width) - 1)

def _set_bit(x, n, value):
    return x & ~(1 << n) | (value << n)

def _set_slice_hl(x, high, low, value):
    mask = (1 << (high - low + 1)) - 1
    return x & ~(mask << low) | ((value & mask) << low)

def _set_slice_w(x, low, width, value):
    mask = (1 << width) - 1
    return x & ~(mask << low) | ((value & mask) << low)

def _sign_extend(x, old_width, new_width):
    if x & (1 << (old_width - 1)):
        for i in range(old_width, new_width):
            x |= 1 << i
        return x
    else:
        return x

def permissions_field_values(permissions, spec_fields):
    ret = collections.OrderedDict()
    for field in spec_fields:
        value = _get_slice_hl(permissions, field.high_bit, field.low_bit)
        if value:
            ret[field.name] = FieldValue(field, value)
    return ret

def permissions_to_str(permissions, spec_fields):
    field_values = permissions_field_values(permissions, spec_fields)
    return ', '.join([value.field.name if value.field.low_bit == value.field.high_bit else str(value) for value in field_values.values() if value.value])

def object_type_to_str(object_type, object_type_map):
    if object_type in object_type_map:
        return '%s (%d)' % (object_type_map[object_type], object_type)
    else:
        return '%d' % object_type

def decode_fields(capability, spec_fields):
    ret = collections.OrderedDict()
    for field in spec_fields:
        value = _get_slice_hl(capability, field.high_bit, field.low_bit)
        description = field.to_string(value) if field.to_string else None
        ret[field.name] = FieldValue(field, value, description)
    return ret

# From Morello alpha1 pseudocode CapGetValueForBound
def _morello_cap_get_value_for_bound(c):
    return _sign_extend(_get_slice_w(c, _MORELLO_ALPHA1_CAP_VALUE_LO_BIT, _MORELLO_ALPHA1_CAP_VALUE_FOR_BOUND_NUM_BITS), _MORELLO_ALPHA1_CAP_VALUE_FOR_BOUND_NUM_BITS, _MORELLO_ALPHA1_CAP_VALUE_NUM_BITS)

# From Morello alpha1 pseudocode CapGetBase
def _morello_cap_get_base(c):
    ie = _get_bit(c, _MORELLO_ALPHA1_CAP_IE_BIT)
    b = _get_slice_w(c, _MORELLO_ALPHA1_CAP_BASE_LO_BIT, _MORELLO_ALPHA1_CAP_MW)
    if ie == 1:
        exp = (_get_slice_hl(c, _MORELLO_ALPHA1_CAP_LIMIT_EXP_HI_BIT, _MORELLO_ALPHA1_CAP_LIMIT_LO_BIT) << (_MORELLO_ALPHA1_CAP_BASE_EXP_HI_BIT - _MORELLO_ALPHA1_CAP_BASE_LO_BIT + 1)) | _get_slice_hl(c, _MORELLO_ALPHA1_CAP_BASE_EXP_HI_BIT, _MORELLO_ALPHA1_CAP_BASE_LO_BIT)
        exp = min(exp, _MORELLO_ALPHA1_CAP_VALUE_NUM_BITS-_MORELLO_ALPHA1_CAP_MW+2)
        b = _set_slice_hl(b, 2, 0, 0)
    else:
        exp = 0
    base = 0
    a = _morello_cap_get_value_for_bound(c)
    a3 = _get_slice_hl(a, exp+_MORELLO_ALPHA1_CAP_MW-1, exp+_MORELLO_ALPHA1_CAP_MW-3)
    b3 = _get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-1, _MORELLO_ALPHA1_CAP_MW-3)
    r = b3 - 1
    if a3 < r:
        if b3 < r:
            cb = 0
        else:
            cb = -1
    else:
        if b3 < r:
            cb = 1
        else:
            cb = 0
    if exp < 50:
        base = _set_slice_hl(base, 63, exp+_MORELLO_ALPHA1_CAP_MW, _get_slice_hl(_get_slice_hl(a, 63, exp+_MORELLO_ALPHA1_CAP_MW) + cb, 63-_MORELLO_ALPHA1_CAP_MW-exp, 0))
    base = _set_slice_hl(base, exp+_MORELLO_ALPHA1_CAP_MW-1, exp, _get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-1, 0))
    base = _set_slice_hl(base, exp-1, 0, 0)
    return base & 0xffffffffffffffff

# From Morello alpha1 pseudocode ExtendLimit
def _morello_extend_limit(t, b, ie):
    if ie == 1:
        base_lo = _get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-3, 3)
        limit_lo = _get_slice_hl(t, _MORELLO_ALPHA1_CAP_MW-3, 3)
    else:
        base_lo = _get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-3, 0)
        limit_lo = _get_slice_hl(t, _MORELLO_ALPHA1_CAP_MW-3, 0)
    if limit_lo < base_lo:
        l_carry_out = 1
    else:
        l_carry_out = 0
    l_msb = ie
    return _get_slice_hl(_get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-1, _MORELLO_ALPHA1_CAP_MW-2) + l_carry_out + l_msb, 1, 0)

# From Morello alpha1 pseudocode CapGetLimit
def _morello_cap_get_limit(c):
    ie = _get_bit(c, _MORELLO_ALPHA1_CAP_IE_BIT)
    b = _get_slice_w(c, _MORELLO_ALPHA1_CAP_BASE_LO_BIT, _MORELLO_ALPHA1_CAP_MW)
    t = _set_slice_w(0, 0, _MORELLO_ALPHA1_CAP_LIMIT_NUM_BITS, _get_slice_w(c, _MORELLO_ALPHA1_CAP_LIMIT_LO_BIT, _MORELLO_ALPHA1_CAP_LIMIT_NUM_BITS))
    if ie == 1:
        exp = (_get_slice_hl(c, _MORELLO_ALPHA1_CAP_LIMIT_EXP_HI_BIT, _MORELLO_ALPHA1_CAP_LIMIT_LO_BIT) << (_MORELLO_ALPHA1_CAP_BASE_EXP_HI_BIT - _MORELLO_ALPHA1_CAP_BASE_LO_BIT + 1)) | _get_slice_hl(c, _MORELLO_ALPHA1_CAP_BASE_EXP_HI_BIT, _MORELLO_ALPHA1_CAP_BASE_LO_BIT)
        exp = min(exp, _MORELLO_ALPHA1_CAP_VALUE_NUM_BITS-_MORELLO_ALPHA1_CAP_MW+2)
        b = _set_slice_hl(b, 2, 0, 0)
        t = _set_slice_hl(t, 2, 0, 0)
    else:
        exp = 0
    t = _set_slice_hl(t, _MORELLO_ALPHA1_CAP_MW-1, _MORELLO_ALPHA1_CAP_MW-2, _morello_extend_limit(_get_slice_w(t, 0, _MORELLO_ALPHA1_CAP_LIMIT_NUM_BITS), b, ie))
    limit = 0
    a = _morello_cap_get_value_for_bound(c)
    a3 = _get_slice_hl(a, exp+_MORELLO_ALPHA1_CAP_MW-1, exp+_MORELLO_ALPHA1_CAP_MW-3)
    b3 = _get_slice_hl(b, _MORELLO_ALPHA1_CAP_MW-1, _MORELLO_ALPHA1_CAP_MW-3)
    t3 = _get_slice_hl(t, _MORELLO_ALPHA1_CAP_MW-1, _MORELLO_ALPHA1_CAP_MW-3)
    r = _get_slice_w(b3 - 1, 0, _MORELLO_ALPHA1_CAP_VALUE_NUM_BITS)
    if a3 < r:
        if t3 < r:
            ct = 0
        else:
            ct = -1
    else:
        if t3 < r:
            ct = 1
        else:
            ct = 0
    if exp < 50:
        limit = _set_slice_hl(limit, 63, exp+_MORELLO_ALPHA1_CAP_MW, _get_slice_hl(_get_slice_hl(a, 63, exp+_MORELLO_ALPHA1_CAP_MW) + ct, 63-_MORELLO_ALPHA1_CAP_MW-exp, 0))
    limit = _set_slice_hl(limit, exp+_MORELLO_ALPHA1_CAP_MW-1, exp, _get_slice_hl(t, _MORELLO_ALPHA1_CAP_MW-1, 0))
    limit = _set_slice_hl(limit, exp-1, 0, 0)
    return limit & 0xffffffffffffffff

def _morello_cap_get_bounds(c):
    return (_morello_cap_get_base(c), _morello_cap_get_limit(c))

# From Morello beta0 ARRAN-596 pseudocode CapGetValueForBound
def _morello_beta0_update_cap_get_value_for_bound(c):
    return _sign_extend(_get_slice_w(c, _MORELLO_BETA0_UPDATE_CAP_VALUE_LO_BIT, _MORELLO_BETA0_UPDATE_CAP_VALUE_FOR_BOUND_NUM_BITS), _MORELLO_BETA0_UPDATE_CAP_VALUE_FOR_BOUND_NUM_BITS, _MORELLO_BETA0_UPDATE_CAP_VALUE_NUM_BITS)

# From Morello beta0 ARRAN-596 pseudocode CapGetBase
def _morello_beta0_update_cap_get_base(c):
    ie = _get_bit(c, _MORELLO_BETA0_UPDATE_CAP_IE_BIT)
    b = _get_slice_w(c, _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT, _MORELLO_BETA0_UPDATE_CAP_MW)
    if ie == 1:
        exp = (_get_slice_hl(c, _MORELLO_BETA0_UPDATE_CAP_LIMIT_EXP_HI_BIT, _MORELLO_BETA0_UPDATE_CAP_LIMIT_LO_BIT) << (_MORELLO_BETA0_UPDATE_CAP_BASE_EXP_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT + 1)) | _get_slice_hl(c, _MORELLO_BETA0_UPDATE_CAP_BASE_EXP_HI_BIT, _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT)
        exp = min(exp, _MORELLO_BETA0_UPDATE_CAP_VALUE_NUM_BITS-_MORELLO_BETA0_UPDATE_CAP_MW+2)
        b = _set_slice_hl(b, 2, 0, 0)
    else:
        exp = 0
    base = 0
    a = _morello_cap_get_value_for_bound(c)
    a3 = _get_slice_hl(a, exp+_MORELLO_BETA0_UPDATE_CAP_MW-1, exp+_MORELLO_BETA0_UPDATE_CAP_MW-3)
    b3 = _get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-1, _MORELLO_BETA0_UPDATE_CAP_MW-3)
    r = b3 - 1
    if a3 < r:
        if b3 < r:
            cb = 0
        else:
            cb = -1
    else:
        if b3 < r:
            cb = 1
        else:
            cb = 0
    if exp < 50 and exp + _MORELLO_BETA0_UPDATE_CAP_MW <= 63:
        base = _set_slice_hl(base, 63, exp+_MORELLO_BETA0_UPDATE_CAP_MW, _get_slice_hl(_get_slice_hl(a, 63, exp+_MORELLO_BETA0_UPDATE_CAP_MW) + cb, 63-_MORELLO_BETA0_UPDATE_CAP_MW-exp, 0))
    base = _set_slice_hl(base, exp+_MORELLO_BETA0_UPDATE_CAP_MW-1, exp, _get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-1, 0))
    base = _set_slice_hl(base, exp-1, 0, 0)
    return base & 0xffffffffffffffff

# From Morello beta0 ARRAN-596 pseudocode ExtendLimit
def _morello_beta0_update_extend_limit(t, b, ie):
    if ie == 1:
        base_lo = _get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-3, 3)
        limit_lo = _get_slice_hl(t, _MORELLO_BETA0_UPDATE_CAP_MW-3, 3)
    else:
        base_lo = _get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-3, 0)
        limit_lo = _get_slice_hl(t, _MORELLO_BETA0_UPDATE_CAP_MW-3, 0)
    if limit_lo < base_lo:
        l_carry_out = 1
    else:
        l_carry_out = 0
    l_msb = ie
    return _get_slice_hl(_get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-1, _MORELLO_BETA0_UPDATE_CAP_MW-2) + l_carry_out + l_msb, 1, 0)

# From Morello beta0 ARRAN-596 pseudocode CapGetLimit
def _morello_beta0_update_cap_get_limit(c):
    ie = _get_bit(c, _MORELLO_BETA0_UPDATE_CAP_IE_BIT)
    b = _get_slice_w(c, _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT, _MORELLO_BETA0_UPDATE_CAP_MW)
    t = _set_slice_w(0, 0, _MORELLO_BETA0_UPDATE_CAP_LIMIT_NUM_BITS, _get_slice_w(c, _MORELLO_BETA0_UPDATE_CAP_LIMIT_LO_BIT, _MORELLO_BETA0_UPDATE_CAP_LIMIT_NUM_BITS))
    if ie == 1:
        exp = (_get_slice_hl(c, _MORELLO_BETA0_UPDATE_CAP_LIMIT_EXP_HI_BIT, _MORELLO_BETA0_UPDATE_CAP_LIMIT_LO_BIT) << (_MORELLO_BETA0_UPDATE_CAP_BASE_EXP_HI_BIT - _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT + 1)) | _get_slice_hl(c, _MORELLO_BETA0_UPDATE_CAP_BASE_EXP_HI_BIT, _MORELLO_BETA0_UPDATE_CAP_BASE_LO_BIT)
        exp = min(exp, _MORELLO_BETA0_UPDATE_CAP_VALUE_NUM_BITS-_MORELLO_BETA0_UPDATE_CAP_MW+2)
        b = _set_slice_hl(b, 2, 0, 0)
        t = _set_slice_hl(t, 2, 0, 0)
    else:
        exp = 0
    t = _set_slice_hl(t, _MORELLO_BETA0_UPDATE_CAP_MW-1, _MORELLO_BETA0_UPDATE_CAP_MW-2, _morello_beta0_update_extend_limit(_get_slice_w(t, 0, _MORELLO_BETA0_UPDATE_CAP_LIMIT_NUM_BITS), b, ie))
    limit = 0
    a = _morello_beta0_update_cap_get_value_for_bound(c)
    a3 = _get_slice_hl(a, exp+_MORELLO_BETA0_UPDATE_CAP_MW-1, exp+_MORELLO_BETA0_UPDATE_CAP_MW-3)
    b3 = _get_slice_hl(b, _MORELLO_BETA0_UPDATE_CAP_MW-1, _MORELLO_BETA0_UPDATE_CAP_MW-3)
    t3 = _get_slice_hl(t, _MORELLO_BETA0_UPDATE_CAP_MW-1, _MORELLO_BETA0_UPDATE_CAP_MW-3)
    r = _get_slice_w((b3 - 1) & 7, 0, _MORELLO_BETA0_UPDATE_CAP_VALUE_NUM_BITS)
    if a3 < r:
        if t3 < r:
            ct = 0
        else:
            ct = -1
    else:
        if t3 < r:
            ct = 1
        else:
            ct = 0
    if exp < 50 and exp + _MORELLO_BETA0_UPDATE_CAP_MW <= 63:
        limit = _set_slice_hl(limit, 63, exp+_MORELLO_BETA0_UPDATE_CAP_MW, _get_slice_hl(_get_slice_hl(a, 63, exp+_MORELLO_BETA0_UPDATE_CAP_MW) + ct, 63-_MORELLO_BETA0_UPDATE_CAP_MW-exp, 0))
    limit = _set_slice_hl(limit, exp+_MORELLO_BETA0_UPDATE_CAP_MW-1, exp, _get_slice_hl(t, _MORELLO_BETA0_UPDATE_CAP_MW-1, 0))
    limit = _set_slice_hl(limit, exp-1, 0, 0)
    return limit & 0xffffffffffffffff

def _morello_beta0_update_cap_get_bounds(c):
    return (_morello_beta0_update_cap_get_base(c), _morello_beta0_update_cap_get_limit(c))

def _morello_beta0_fixed_cap_is_internal_exponent(c):
    return _get_bit(c, _MORELLO_BETA0_FIXED_CAP_IE_BIT) == 0

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetExponent
def _morello_beta0_fixed_cap_get_exponent(c):
    if _morello_beta0_fixed_cap_is_internal_exponent(c):
        nexp = (_get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_LIMIT_EXP_HI_BIT, _MORELLO_BETA0_FIXED_CAP_LIMIT_LO_BIT) << \
                    (_MORELLO_BETA0_FIXED_CAP_BASE_EXP_HI_BIT - _MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT + 1)) | \
               _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_BASE_EXP_HI_BIT, _MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT)
        assert (_MORELLO_BETA0_FIXED_CAP_LIMIT_EXP_HI_BIT + _MORELLO_BETA0_FIXED_CAP_BASE_EXP_HI_BIT - \
                _MORELLO_BETA0_FIXED_CAP_LIMIT_LO_BIT - _MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT + 2) == 6
        return 0x3f & ~nexp
    else:
        return 0

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetEffectiveExponent
def _morello_beta0_fixed_cap_get_effective_exponent(c):
    exp = _morello_beta0_fixed_cap_get_exponent(c)
    if exp < _MORELLO_BETA0_FIXED_CAP_MAX_EXPONENT:
        return exp
    else:
        return _MORELLO_BETA0_FIXED_CAP_MAX_EXPONENT

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetBottom
def _morello_beta0_fixed_cap_get_bottom(c):
    if _morello_beta0_fixed_cap_is_internal_exponent(c):
        return _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_BASE_HI_BIT, _MORELLO_BETA0_FIXED_CAP_BASE_MANTISSA_LO_BIT) << 3
    else:
        return _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_BASE_HI_BIT, _MORELLO_BETA0_FIXED_CAP_BASE_LO_BIT)

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetTop
def _morello_beta0_fixed_cap_get_top(c):
    lmsb = 0
    lcarry = 0
    b = _morello_beta0_fixed_cap_get_bottom(c)
    if _morello_beta0_fixed_cap_is_internal_exponent(c):
        lmsb = 1
        t = _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_LIMIT_HI_BIT, _MORELLO_BETA0_FIXED_CAP_LIMIT_MANTISSA_LO_BIT) << 3
    else:
        t = _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_LIMIT_HI_BIT, _MORELLO_BETA0_FIXED_CAP_LIMIT_LO_BIT)
    if _morello_beta0_fixed_cap_unsigned_less_than(_get_slice_hl(t, _MORELLO_BETA0_FIXED_CAP_MW-3, 0), \
                                                   _get_slice_hl(b, _MORELLO_BETA0_FIXED_CAP_MW-3, 0)):
        lcarry = 1
    t = _set_slice_hl(t, _MORELLO_BETA0_FIXED_CAP_MW-1, _MORELLO_BETA0_FIXED_CAP_MW-2, \
            _get_slice_hl(b, _MORELLO_BETA0_FIXED_CAP_MW-1, _MORELLO_BETA0_FIXED_CAP_MW-2) + lmsb + lcarry)
    return t

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetValue
def _morello_beta0_fixed_cap_get_value(c):
    return _get_slice_hl(c, _MORELLO_BETA0_FIXED_CAP_VALUE_HI_BIT, _MORELLO_BETA0_FIXED_CAP_VALUE_LO_BIT)

# From Morello beta0 fixed CHERI concentrate pseudocode CapUnsignedLessThan
def _morello_beta0_fixed_cap_unsigned_less_than(a, b):
    return a < b

# From Morello beta0 fixed CHERI concentrate pseudocode CapUnsignedGreaterThan
def _morello_beta0_fixed_cap_unsigned_greater_than(a, b):
    return a > b

# From Morello beta0 fixed CHERI concentrate pseudocode CapGetBounds
def _morello_beta0_fixed_cap_get_bounds(c):
    exp = _morello_beta0_fixed_cap_get_effective_exponent(c)
    bottom = _morello_beta0_fixed_cap_get_bottom(c)
    top = _morello_beta0_fixed_cap_get_top(c)
    base = 0
    limit = 0
    base = _set_slice_hl(base, exp+_MORELLO_BETA0_FIXED_CAP_MW-1, exp, bottom)
    limit = _set_slice_hl(limit, exp+_MORELLO_BETA0_FIXED_CAP_MW-1, exp, top)
    a = _morello_beta0_fixed_cap_get_value(c)
    A3 = _get_slice_hl(a, exp+_MORELLO_BETA0_FIXED_CAP_MW-1, exp+_MORELLO_BETA0_FIXED_CAP_MW-3)
    B3 = _get_slice_hl(bottom, _MORELLO_BETA0_FIXED_CAP_MW-1, _MORELLO_BETA0_FIXED_CAP_MW-3)
    T3 = _get_slice_hl(top, _MORELLO_BETA0_FIXED_CAP_MW-1, _MORELLO_BETA0_FIXED_CAP_MW-3)
    R3 = (B3 - 1) & 0x7

    if _morello_beta0_fixed_cap_unsigned_less_than(A3, R3):
        aHi = 1
    else:
        aHi = 0

    if _morello_beta0_fixed_cap_unsigned_less_than(B3, R3):
        bHi = 1
    else:
        bHi = 0

    if _morello_beta0_fixed_cap_unsigned_less_than(T3, R3):
        tHi = 1
    else:
        tHi = 0

    correction_base = bHi - aHi
    correction_limit = tHi - aHi

    if exp+_MORELLO_BETA0_FIXED_CAP_MW < _MORELLO_BETA0_FIXED_CAP_MAX_EXPONENT+_MORELLO_BETA0_FIXED_CAP_MW:
        atop = _get_slice_hl(a, 65, exp+_MORELLO_BETA0_FIXED_CAP_MW)
        base = _set_slice_hl(base, 65, exp+_MORELLO_BETA0_FIXED_CAP_MW, atop + correction_base)
        limit = _set_slice_hl(limit, 65, exp+_MORELLO_BETA0_FIXED_CAP_MW, atop + correction_limit)

    l2 = _get_slice_hl(limit, 64, 63)
    b2 = _get_bit(base, 63)
    if exp < (_MORELLO_BETA0_FIXED_CAP_MAX_EXPONENT-1) and _morello_beta0_fixed_cap_unsigned_greater_than((l2 - b2) & 0x3, 1):
        limit = _set_bit(limit, 64, 1 & ~_get_bit(limit, 64))

    return (_get_slice_hl(base, 63, 0), _get_slice_hl(limit, 64, 0))

# From Morello beta1 pseudocode CapIsInternalExponent
def _morello_beta1_cap_is_internal_exponent(c):
    return _get_bit(c, _MORELLO_BETA1_CAP_IE_BIT) == 0

# From Morello beta1 pseudocode CapGetExponent
def _morello_beta1_cap_get_exponent(c):
    if _morello_beta1_cap_is_internal_exponent(c):
        nexp = (_get_slice_hl(c, _MORELLO_BETA1_CAP_LIMIT_EXP_HI_BIT, _MORELLO_BETA1_CAP_LIMIT_LO_BIT) << \
                    (_MORELLO_BETA1_CAP_BASE_EXP_HI_BIT - _MORELLO_BETA1_CAP_BASE_LO_BIT + 1)) | \
               _get_slice_hl(c, _MORELLO_BETA1_CAP_BASE_EXP_HI_BIT, _MORELLO_BETA1_CAP_BASE_LO_BIT)
        assert (_MORELLO_BETA1_CAP_LIMIT_EXP_HI_BIT + _MORELLO_BETA1_CAP_BASE_EXP_HI_BIT - \
                _MORELLO_BETA1_CAP_LIMIT_LO_BIT - _MORELLO_BETA1_CAP_BASE_LO_BIT + 2) == 6
        return 0x3f & ~nexp
    else:
        return 0

# From Morello beta1 pseudocode CapGetEffectiveExponent
def _morello_beta1_cap_get_effective_exponent(c):
    exp = _morello_beta1_cap_get_exponent(c)
    if exp < _MORELLO_BETA1_CAP_MAX_EXPONENT:
        return exp
    else:
        return _MORELLO_BETA1_CAP_MAX_EXPONENT

# From Morello beta1 pseudocode CapGetBottom
def _morello_beta1_cap_get_bottom(c):
    if _morello_beta1_cap_is_internal_exponent(c):
        return _get_slice_hl(c, _MORELLO_BETA1_CAP_BASE_HI_BIT, _MORELLO_BETA1_CAP_BASE_MANTISSA_LO_BIT) << 3
    else:
        return _get_slice_hl(c, _MORELLO_BETA1_CAP_BASE_HI_BIT, _MORELLO_BETA1_CAP_BASE_LO_BIT)

# From Morello beta1 pseudocode CapGetTop
def _morello_beta1_cap_get_top(c):
    lmsb = 0
    lcarry = 0
    b = _morello_beta1_cap_get_bottom(c)
    if _morello_beta1_cap_is_internal_exponent(c):
        lmsb = 1
        t = _get_slice_hl(c, _MORELLO_BETA1_CAP_LIMIT_HI_BIT, _MORELLO_BETA1_CAP_LIMIT_MANTISSA_LO_BIT) << 3
    else:
        t = _get_slice_hl(c, _MORELLO_BETA1_CAP_LIMIT_HI_BIT, _MORELLO_BETA1_CAP_LIMIT_LO_BIT)
    if _morello_beta1_cap_unsigned_less_than(_get_slice_hl(t, _MORELLO_BETA1_CAP_MW-3, 0), \
                                            _get_slice_hl(b, _MORELLO_BETA1_CAP_MW-3, 0)):
        lcarry = 1
    t = _set_slice_hl(t, _MORELLO_BETA1_CAP_MW-1, _MORELLO_BETA1_CAP_MW-2, \
            _get_slice_hl(b, _MORELLO_BETA1_CAP_MW-1, _MORELLO_BETA1_CAP_MW-2) + lmsb + lcarry)
    return t

# From Morello beta1 pseudocode CapGetValue
def _morello_beta1_cap_get_value(c):
    return _get_slice_hl(c, _MORELLO_BETA1_CAP_VALUE_HI_BIT, _MORELLO_BETA1_CAP_VALUE_LO_BIT)

# From Morello beta1 pseudocode CapBoundsAddress
def _morello_beta1_cap_bounds_address(address):
    return _sign_extend(_get_slice_hl(address, _MORELLO_BETA1_CAP_FLAGS_LO_BIT-1, 0), _MORELLO_BETA1_CAP_FLAGS_LO_BIT, _MORELLO_BETA1_CAP_VALUE_NUM_BITS)

# From Morello beta1 pseudocode CapUnsignedLessThan
def _morello_beta1_cap_unsigned_less_than(a, b):
    return a < b

# From Morello beta1 pseudocode CapUnsignedGreaterThan
def _morello_beta1_cap_unsigned_greater_than(a, b):
    return a > b

# From Morello beta1 pseudocode CapGetBounds
def _morello_beta1_cap_get_bounds(c):
    exp = _morello_beta1_cap_get_effective_exponent(c)
    bottom = _morello_beta1_cap_get_bottom(c)
    top = _morello_beta1_cap_get_top(c)
    base = 0
    limit = 0
    base = _set_slice_hl(base, exp+_MORELLO_BETA1_CAP_MW-1, exp, bottom)
    limit = _set_slice_hl(limit, exp+_MORELLO_BETA1_CAP_MW-1, exp, top)

    a = _morello_beta1_cap_bounds_address(_morello_beta1_cap_get_value(c))
    A3 = _get_slice_hl(a, exp+_MORELLO_BETA1_CAP_MW-1, exp+_MORELLO_BETA1_CAP_MW-3)
    B3 = _get_slice_hl(bottom, _MORELLO_BETA1_CAP_MW-1, _MORELLO_BETA1_CAP_MW-3)
    T3 = _get_slice_hl(top, _MORELLO_BETA1_CAP_MW-1, _MORELLO_BETA1_CAP_MW-3)
    R3 = (B3 - 1) & 0x7

    if _morello_beta1_cap_unsigned_less_than(A3, R3):
        aHi = 1
    else:
        aHi = 0

    if _morello_beta1_cap_unsigned_less_than(B3, R3):
        bHi = 1
    else:
        bHi = 0

    if _morello_beta1_cap_unsigned_less_than(T3, R3):
        tHi = 1
    else:
        tHi = 0

    correction_base = bHi - aHi
    correction_limit = tHi - aHi
    print("R3 :", hex(R3))
    print("A3 :", hex(A3), "T3:", hex(T3))
    print("A3 :", hex(A3), "B3:", hex(B3))
    print("aHi :", hex(aHi), "bHi:", hex(bHi))
    print("aHi :", hex(aHi), "tHi:", hex(tHi))
    if exp+_MORELLO_BETA1_CAP_MW < _MORELLO_BETA1_CAP_MAX_EXPONENT+_MORELLO_BETA1_CAP_MW:
        atop = _get_slice_hl(a, 65, exp+_MORELLO_BETA1_CAP_MW)
        base = _set_slice_hl(base, 65, exp+_MORELLO_BETA1_CAP_MW, atop + correction_base)
        limit = _set_slice_hl(limit, 65, exp+_MORELLO_BETA1_CAP_MW, atop + correction_limit)

    l2 = _get_slice_hl(limit, 64, 63)
    b2 = _get_bit(base, 63)
    if exp < (_MORELLO_BETA1_CAP_MAX_EXPONENT-1) and _morello_beta1_cap_unsigned_greater_than((l2 - b2) & 0x3, 1):
        limit = _set_bit(limit, 64, 1 & ~_get_bit(limit, 64))

    return (_get_slice_hl(base, 63, 0), _get_slice_hl(limit, 64, 0))

# From Morello beta1 ARRAN-822 CapIsExponentOutOfRange
def _morello_beta1_arran_822_cap_is_exponent_out_of_range(c):
    exp = _morello_beta1_cap_get_exponent(c)
    return _MORELLO_BETA1_CAP_MAX_EXPONENT < exp < _MORELLO_BETA1_ARRAN_822_CAP_MAX_ENCODEABLE_EXPONENT

# From Morello beta1 ARRAN 822 CapGetBounds
def _morello_beta1_arran_822_cap_get_bounds(c):
    exp = _morello_beta1_cap_get_exponent(c)
    if exp == _MORELLO_BETA1_ARRAN_822_CAP_MAX_ENCODEABLE_EXPONENT:
        return (_MORELLO_BETA1_ARRAN_822_CAP_BOUND_MIN, _MORELLO_BETA1_ARRAN_822_CAP_BOUND_MAX)
    elif _morello_beta1_arran_822_cap_is_exponent_out_of_range(c):
        return (_MORELLO_BETA1_ARRAN_822_CAP_BOUND_MIN, _MORELLO_BETA1_ARRAN_822_CAP_BOUND_MAX)
    else:
        return _morello_beta1_cap_get_bounds(c)

MORELLO_SPEC_VERSION_TO_DECODE = {
    MORELLO_ALPHA1:                        _morello_cap_get_bounds,
    MORELLO_BETA0:                         _morello_cap_get_bounds,
    MORELLO_BETA0_UPDATE:                  _morello_beta0_update_cap_get_bounds,
    MORELLO_BETA0_FIXED_CHERI_CONCENTRATE: _morello_beta0_fixed_cap_get_bounds,
    MORELLO_BETA1:                         _morello_beta1_cap_get_bounds,
    MORELLO_BETA1_ARRAN_822:               _morello_beta1_arran_822_cap_get_bounds
}

def get_rep_range(c, base):
    exp = _morello_beta1_cap_get_exponent(c)
    print(exp)
    if exp > _MORELLO_BETA1_CAP_MAX_EXPONENT - 2:
        RepB = 0
        RepT = 2**(64)
    else:
        B3 = _get_slice_hl(base, _MORELLO_BETA1_CAP_VALUE_HI_BIT-1, (_MORELLO_BETA1_CAP_MW-3+exp))
        R3 = B3 - 1
        print(hex(base), hex(B3), hex(R3))
        RepB = R3 << (_MORELLO_BETA1_CAP_MW - 3 + exp)
        RepT = RepB + 2**(exp + _MORELLO_BETA1_CAP_MW)
        if RepB < 0:
            RepB = 2**64 + RepB
    return RepB, RepT

def decode_capability(capability, spec_version=DEFAULT_SPEC_VERSION):
    if spec_version in MORELLO_SPEC_VERSIONS:
        fields_spec = MORELLO_SPEC_VERSION_TO_FIELDS[spec_version]
        decode_function = MORELLO_SPEC_VERSION_TO_DECODE[spec_version]
    else:
        raise ValueError('Unsupported specification version: %s' % spec_version)
    fields = decode_fields(capability, fields_spec)
    (base, limit) = decode_function(capability)
    (RepB, RepT) = get_rep_range(capability, base)
    fields['_Base'] = FieldValue.from_name_and_value('Base', base)
    fields['_RepB'] = FieldValue.from_name_and_value('RepB', RepB)
    fields['_Limit'] = FieldValue.from_name_and_value('Limit', limit)
    fields['_RepT'] = FieldValue.from_name_and_value('RepT', RepT)
    fields['_exp'] = FieldValue.from_name_and_value('exp', _morello_beta1_cap_get_exponent(capability))
    return fields

def format_field_values(capability, field_values):
    ret = ''
    ret += '0x{:017x}'.format(capability)
    ret += '\n'
    ret += '  '
    for x in range(32, 0, -1):
        ret += '{:>5d}'.format((x - 1) * 4)
    ret += '\n'
    ret += '=' * (5 * 32 + 2)
    ret += '\n'
    ret += ' {:1x}'.format(_get_slice_w(capability, 32 * 4, 4))
    for x in range(32, 0, -1):
        ret += '    {:x}'.format(_get_slice_w(capability, (x - 1) * 4, 4))
    ret += '\n'
    ret += ' '
    for x in range(129, 0, -1):
        if (x % 4) == 0:
            ret += ' '
        ret += '{:d}'.format(_get_slice_w(capability, x - 1, 1))
    ret += '\n'
    field_value_by_high_bit = {}
    for field_value in [field_value for field_value in field_values.values() if field_value.field]:
        field_value_by_high_bit[(field_value.field.high_bit, field_value.field.low_bit)] = field_value
    field_value_by_high_bit = [v for k, v in sorted(field_value_by_high_bit.items(), reverse=True)]
    for field_value in field_value_by_high_bit:
        pad = 128 - field_value.field.high_bit
        if pad > 0:
            pad += (pad // 4) + 2
        else:
            pad += 1
        description = field_value.description if field_value.description else hex(field_value.value)
        width = (field_value.field.high_bit + (field_value.field.high_bit // 4)) - (field_value.field.low_bit + (field_value.field.low_bit // 4)) + 1
        ret += (' ' * pad)
        if width > 2:
            ret += '|' + ('-' * (width - 2)) + '| '
        elif width == 2:
            ret += '||'
        else:
            ret += '|'
        ret += ' '
        ret += field_value.name + ' ' + description
        ret += '\n'
    extra_fields = []
    for field_value in [field_value for field_value in field_values.values() if not field_value.field]:
        description = field_value.description if field_value.description else hex(field_value.value)
        extra_fields.append( (field_value.name, description) )
    extra_fields = sorted(extra_fields)
    max_name_len = 0
    max_hex_len = 0
    for (name, description) in extra_fields:
        max_name_len = max(max_name_len, len(name))
        if description.startswith('0x'):
            max_hex_len = max(max_hex_len, len(description))
    for (name, description) in extra_fields:
        ret += name.ljust(max_name_len) + ' '
        if description.startswith('0x'):
            ret += '0x' + description[2:].rjust(max_hex_len-2, '0')
        else:
            ret += description
        ret += '\n'
    return ret

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Decode a Morello / Arran capability',
                                     epilog='Available specification versions:' + \
                                         '\n  '.join([''] + MORELLO_SPEC_VERSIONS),
                                     formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument('capability', help='value of capability to decode', metavar='CAPABILITY')
    parser.add_argument('--spec-version', help='version of specification to use (%s)' % DEFAULT_SPEC_VERSION, default=DEFAULT_SPEC_VERSION)
    args = parser.parse_args()
    capability = int(args.capability, 0)
    field_values = decode_capability(capability, args.spec_version)
    print(format_field_values(capability, field_values))
