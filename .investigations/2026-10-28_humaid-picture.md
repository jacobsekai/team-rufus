# Investigation: Humaid picture missing from deployed site

**Date:** 2026-10-28
**Trigger:** User reported that Humaid's picture was missing from the deployed CloudFront website.
**Status:** Resolved

## Observations

- Current `frontend/digital.html` uses `pictures/placeholder image.png` for the Digital Software Development hero and has no Humaid image reference.
- Current `frontend/styles/people-photos.css` still contains `.person-photo--humaid { object-position: 50% 82%; }`.
- Both `frontend/pictures/humaid img.png` and `frontend/pictures/humaid.jpg` are tracked in Git.
- Commit `6d4e9f2` added `frontend/pictures/humaid img.png` and changed the Digital hero to use it.
- The current merge commit `d067302` retains the asset but the Digital hero uses the placeholder again.
- Unauthenticated requests to the CloudFront root, a page path, and candidate image paths return HTTP 403 with the CloudFrontSigner auth page. The public `/js/cfs-handler.js` path is accessible.

## Hypothesis 1: The Humaid asset was not uploaded

**Prediction:** The source tree or merge result would not contain the Humaid asset, or deployment logic would exclude it.
**Experiment:** Inspected tracked assets, the merge result, and `deploy/deploy.sh`.
**Result:** The asset is present in the merge result. `deploy/deploy.sh` copies all files under `frontend/.` and synchronizes them to the frontend bucket.
**Verdict:** Rejected.

## Hypothesis 2: A merge replaced the image reference with the placeholder

**Prediction:** Git history would show a Humaid reference in the photo commit and a placeholder reference in the current merged source, with the Humaid asset retained.
**Experiment:** Compared `6d4e9f2` with `d067302` and inspected current HTML/CSS.
**Result:** `6d4e9f2` references `pictures/humaid img.png`; `d067302` references `pictures/placeholder image.png`; the Humaid asset and Humaid crop CSS remain.
**Verdict:** Confirmed.

## Hypothesis 3: CloudFront cache alone is serving stale content

**Prediction:** Current source would reference Humaid and deployment would need only invalidation, or the deployment script would lack invalidation.
**Experiment:** Inspected current source and `deploy/deploy.sh`.
**Result:** Current source itself references the placeholder, and the deployment script invalidates `/*` after upload.
**Verdict:** Rejected as the primary cause.

## Conclusion

**Root Cause / Answer:** The image reference was lost during the merge that produced `d067302`; the tracked photo remains, but `frontend/digital.html` reverted to the placeholder. The smallest fix is to restore the Humaid image reference and `person-photo--humaid` class in that hero, then deploy and verify with Midway authentication.

**Evidence:** Current HTML, orphaned crop CSS, tracked assets, the `6d4e9f2` photo diff, the `d067302` merge result, and the CloudFront 403 authentication response.

**Action Taken:** No code, deployment, commit, or server was changed. Findings were written to `.agents/tasks/investigate-humaid-picture.md`.
