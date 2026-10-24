SELECT COUNT(DISTINCT object_id) AS approved_sculpture_count
FROM object_physical_properties
WHERE BTRIM(classification) IN (
    'Bark-Sculpture',
    'Beads-Sculpture',
    'Bone/Ivory-Sculpture',
    'Ceramics-Sculpture',
    'Metal-Sculpture',
    'Sculpture',
    'Sculpture-Alabaster',
    'Sculpture-Architectural',
    'Sculpture-Architectural-Stone',
    'Sculpture-Bronze',
    'Sculpture-Ceramics',
    'Sculpture-Miniature',
    'Sculpture-Stone',
    'Sculpture-Wood',
    'Stone Sculpture',
    'Stone-Sculpture',
    'Wood-Sculpture'
);

SELECT COUNT(DISTINCT object_id) AS proposed_sculpture_count
FROM object_physical_properties
WHERE BTRIM(classification) IN (
    'Sculpture'
);
