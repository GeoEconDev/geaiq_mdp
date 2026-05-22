DELETE `wh.observable_scales`
WHERE uuid IN (
SELECT ABSSCAL.uuid
FROM `wh.observable_scales` ABSSCAL
LEFT JOIN `wh.observable_scales` CONCAL ON (CONCAL.abstract_scale_uuid = ABSSCAL.uuid)
WHERE CONCAL.uuid IS NULL AND ABSSCAL.group_uuid IS NULL
);