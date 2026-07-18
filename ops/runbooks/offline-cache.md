# Runbook: offline / cache behavior

## Expectation

Xibo players cache layouts and required media so short CMS outages do not immediately blackout the floor.

## Verify

1. Schedule a known layout to a test display.
2. Allow the player to fully download required files.
3. Disconnect CMS network path (or stop CMS briefly in a lab).
4. Confirm the player continues the cached schedule.
5. Restore connectivity; confirm the player resumes CMS communication without manual wipe.

## If cache is stale after content update

1. Confirm media sync and layout publish in CMS.
2. Force a display status refresh / collect from CMS as appropriate for your player version.
3. Reboot the Pi only if the player is wedged.
4. Avoid deleting the player library unless directed by Xibo recovery docs.
