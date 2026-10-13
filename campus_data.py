"""Default campus setup, loaded into the database on first start.

Administrators can rename, move, hide or add places later in
Admin -> Campus locations (click the map to place them), and change the
campus name and map centre in Admin -> Settings.
"""

CAMPUS_NAME = "campusfound"

# Map centre and default zoom. Change these (or use Admin -> Settings) to put
# the map on your own campus.
CAMPUS_LAT = 12.8003
CAMPUS_LNG = 80.2260
CAMPUS_ZOOM = 17

# Email domains allowed to register (sub-domains included).
# Empty = any email address can register.
EMAIL_DOMAINS = []

# (name, latitude, longitude, approved hand-over point?)
LOCATIONS = [
    ("Main Gate", 12.8009459, 80.2240157, True),
    ("Main Block", 12.8009078, 80.2243969, True),
    ("Library", 12.8019789, 80.2259790, True),
    ("Canteen", 12.8006248, 80.2251301, False),
    ("Cafeteria", 12.8009524, 80.2263220, False),
    ("Laboratory", 12.8017204, 80.2253759, False),
    ("Computer Science Block", 12.7999048, 80.2265418, False),
    ("Administrative Block", 12.7999886, 80.2256660, True),
    ("Auditorium", 12.8005683, 80.2255804, False),
    ("Ground", 12.8014838, 80.2256379, False),
    ("Parking", 12.7996057, 80.2264757, False),
    ("Hostel", 12.7968083, 80.2275461, False),
]
