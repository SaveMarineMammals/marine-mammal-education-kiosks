# Runbook: retire an exhibit

1. Set `exhibit.yaml` `status` to `retired` (do not delete the folder).
2. Update `_catalog.yaml` accordingly.
3. In CMS: remove or expire schedules that reference the exhibit’s layouts/campaigns.
4. Optionally retire Library media (Xibo “retire” keeps existing assignments but hides from new picks) or leave tagged for archive.
5. Keep media-store objects; do not purge until retention policy says so.
6. Attract-loop / other exhibits should continue uninterrupted on affected display groups.
