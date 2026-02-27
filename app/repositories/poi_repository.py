"""POI repository compatibility facade.

This module keeps legacy storage implementation (`idle_land` table)
while exposing a POI-oriented repository name to service and test layers.
"""

from app.repositories.idle_land_repository import *  # noqa: F403

