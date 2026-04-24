BEGIN;

TRUNCATE TABLE
  candidate_files,
  candidate_comments,
  interview_scorecards,
  interview_schedules,
  candidates
RESTART IDENTITY CASCADE;

COMMIT;
