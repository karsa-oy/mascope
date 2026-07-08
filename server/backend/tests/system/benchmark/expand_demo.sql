-- Scale a demo batch to benchmark size by cloning, inside one transaction:
--   1. the target collection's compounds/ions `imult` times (bigger collection)
--   2. the batch's samples `mult` times, with every ion-level match row
--
-- Idempotent. Cloned rows are tagged with a "[bench-clone ...]" marker in their
-- name, and only the unmarked *seed* rows (the pristine dataset) are ever
-- cloned, so a re-run regenerates the same deterministic ids and ON CONFLICT
-- skips them. This also means changing the multipliers needs a fresh restore
-- (the seed is cloned by the current multipliers; an existing larger clone set
-- is left untouched, never shrunk).
--
-- Parameters (all required, passed with -v):
--   batch       source sample_batch_id whose samples are cloned
--   collection  target_collection_id whose ions are cloned (must be on `batch`)
--   imult       collection-ion generations to add (0 = leave collection as is)
--   mult        sample generations to add (0 = leave batch as is)
--
-- Cloning happens at the SQL level: the chart and match-record endpoints read
-- these rows directly, so no raw files or reprocessing are needed. The result
-- is representative for read/query benchmarks, not for pipeline correctness.

\set ON_ERROR_STOP on
\set marker '[bench-clone'
\timing on

BEGIN;

-- ---------- Seed sets (pristine, unmarked rows only) ----------
CREATE TEMP TABLE seed_sample ON COMMIT DROP AS
SELECT sample_item_id AS id
FROM sample_item
WHERE sample_batch_id = :'batch'
  AND sample_item_name NOT LIKE '%' || :'marker' || '%';

CREATE TEMP TABLE seed_ion ON COMMIT DROP AS
SELECT ti.target_ion_id AS ion_id, ti.target_compound_id AS compound_id
FROM target_ion ti
JOIN target_compound_in_target_collection tcc
  ON tcc.target_compound_id = ti.target_compound_id
JOIN target_compound tc ON tc.target_compound_id = ti.target_compound_id
WHERE tcc.target_collection_id = :'collection'
  AND tc.target_compound_name NOT LIKE '%' || :'marker' || '%';

-- ---------- Phase 1: enlarge the target collection ----------
CREATE TEMP TABLE ion_clone_map ON COMMIT DROP AS
SELECT si.ion_id AS orig_ion_id,
       si.compound_id AS orig_compound_id,
       substr(md5(si.ion_id || ':i' || g.g), 1, 16) AS new_ion_id,
       substr(md5(si.compound_id || ':i' || g.g), 1, 16) AS new_compound_id,
       g.g AS gen
FROM seed_ion si
CROSS JOIN generate_series(1, :imult) AS g(g);

INSERT INTO target_compound (target_compound_id, target_compound_name,
                             target_compound_formula, cas_number)
SELECT DISTINCT ON (icm.new_compound_id)
       icm.new_compound_id,
       tc.target_compound_name || ' ' || :'marker' || ' i' || icm.gen || ']',
       tc.target_compound_formula, tc.cas_number
FROM target_compound tc
JOIN ion_clone_map icm ON icm.orig_compound_id = tc.target_compound_id
ON CONFLICT (target_compound_id) DO NOTHING;

INSERT INTO target_ion (target_ion_id, target_compound_id,
                        ionization_mechanism_id, target_ion_formula, filter_params)
SELECT icm.new_ion_id, icm.new_compound_id,
       ti.ionization_mechanism_id, ti.target_ion_formula, ti.filter_params
FROM target_ion ti
JOIN ion_clone_map icm ON icm.orig_ion_id = ti.target_ion_id
ON CONFLICT (target_ion_id) DO NOTHING;

INSERT INTO target_compound_in_target_collection (target_compound_id, target_collection_id)
SELECT DISTINCT icm.new_compound_id, :'collection'
FROM ion_clone_map icm
ON CONFLICT (target_compound_id, target_collection_id) DO NOTHING;

-- Match rows for the cloned ions on the SEED samples only (so the set of
-- matches on seed samples is stable across re-runs; the cloned samples pick
-- these up in phase 2).
INSERT INTO match_ion (match_ion_id, sample_item_id, target_ion_id, match_score,
                       match_category, sample_peak_intensity_sum,
                       match_ion_utc_created, match_ion_utc_modified)
SELECT substr(md5(mi.match_ion_id || ':i' || icm.gen), 1, 32), mi.sample_item_id,
       icm.new_ion_id, mi.match_score, mi.match_category,
       mi.sample_peak_intensity_sum, mi.match_ion_utc_created, mi.match_ion_utc_modified
FROM match_ion mi
JOIN ion_clone_map icm ON icm.orig_ion_id = mi.target_ion_id
JOIN seed_sample ss ON ss.id = mi.sample_item_id
ON CONFLICT (match_ion_id) DO NOTHING;

-- ---------- Phase 2: enlarge the batch ----------
CREATE TEMP TABLE sample_clone_map ON COMMIT DROP AS
SELECT ss.id AS orig_id,
       substr(md5(ss.id || ':s' || g.g), 1, 16) AS new_id,
       g.g AS gen
FROM seed_sample ss
CROSS JOIN generate_series(1, :mult) AS g(g);

INSERT INTO sample_item (
    sample_item_id, sample_batch_id, sample_file_id, sample_item_name,
    sample_item_type, locked, sample_item_attributes, filter_id, tic, polarity,
    ionization_mode_id, t0, t1, sample_item_utc_created, sample_item_utc_modified
)
SELECT scm.new_id, si.sample_batch_id, si.sample_file_id,
       si.sample_item_name || ' ' || :'marker' || ' s' || scm.gen || ']',
       si.sample_item_type, si.locked, si.sample_item_attributes, si.filter_id,
       si.tic, si.polarity, si.ionization_mode_id, si.t0, si.t1,
       si.sample_item_utc_created + (scm.gen || ' minutes')::interval,
       si.sample_item_utc_modified
FROM sample_item si
JOIN sample_clone_map scm ON scm.orig_id = si.sample_item_id
ON CONFLICT (sample_item_id) DO NOTHING;

-- Clone every match on a seed sample (original + phase-1 cloned ions) onto the
-- new samples.
INSERT INTO match_ion (
    match_ion_id, sample_item_id, target_ion_id, match_score, match_category,
    sample_peak_intensity_sum, match_ion_utc_created, match_ion_utc_modified
)
SELECT substr(md5(mi.match_ion_id || ':s' || scm.gen), 1, 32), scm.new_id,
       mi.target_ion_id, mi.match_score, mi.match_category,
       mi.sample_peak_intensity_sum, mi.match_ion_utc_created,
       mi.match_ion_utc_modified
FROM match_ion mi
JOIN sample_clone_map scm ON scm.orig_id = mi.sample_item_id
ON CONFLICT (match_ion_id) DO NOTHING;

-- Benchmarks exercise read paths; make sure the batch is not locked out of
-- the copy/delete endpoints.
UPDATE sample_batch SET locked = 0 WHERE sample_batch_id = :'batch';

COMMIT;

ANALYZE sample_item;
ANALYZE match_ion;
ANALYZE target_ion;
ANALYZE target_compound;
ANALYZE target_compound_in_target_collection;
