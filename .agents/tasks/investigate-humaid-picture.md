# Investigation: Humaid picture missing from deployed site

## Summary answer

The local source no longer references Humaid's image in the Digital Software Development hero. `frontend/digital.html` currently points to `pictures/placeholder image.png`, even though the repository contains both `frontend/pictures/humaid img.png` and `frontend/pictures/humaid.jpg`. Git history shows that commit `6d4e9f2` added Humaid's image to that hero as `pictures/humaid img.png`, and the later merge/update that produced `d067302` replaced that line with the placeholder while bringing in the newer navigation/content version of `digital.html`.

The likely cause is therefore a source-reference regression during the recent merge, followed by a normal deployment of the resulting source. It is not an absent local asset. A direct unauthenticated request to CloudFront cannot expose the deployed HTML or image status because this distribution requires CloudFrontSigner/Midway authentication; it returns the same 403 auth page for `/`, `engineering.html`, and candidate image paths. That response verifies the deployed endpoint is protected, but does not by itself prove the visual page contents for an authenticated visitor.

## Evidence

### Local source and assets

- `frontend/digital.html`, hero image markup in the first `.content-section`: the current source is `src="pictures/placeholder image.png"` with `alt="Homepage image"`. There is no `humaid` reference in the current HTML.
- `frontend/styles/people-photos.css`, `.person-photo--humaid`: the stylesheet still contains a Humaid-specific crop rule, `object-position: 50% 82%`. This is currently orphaned because no current HTML uses that class.
- Tracked assets from `git ls-files 'frontend/pictures/*'` include:
  - `frontend/pictures/humaid img.png`
  - `frontend/pictures/humaid.jpg`
  - `frontend/pictures/placeholder image.png`
- The file named `frontend/pictures/humaid img.png` is tracked and contains JPEG image data (3160x4208). The file named `frontend/pictures/humaid.jpg` is also tracked and contains JPEG image data (1200x1600). The unusual `.png`/JPEG mismatch is worth correcting only if the team chooses to clean up naming; it does not prevent S3 from uploading the file or the browser from loading it when referenced.

### Git history

- Commit `2ba8e69` (`Add team member photos to home, digital and blog`) originally referenced Humaid in `frontend/digital.html` as:
  `class="homepage-image person-photo person-photo--humaid" src="pictures/humaid.jpg"`.
- Commit `6d4e9f2` (`-Added pictures to replace the placeholder images`, 2026-10-28 11:29:41 UTC) changed the Digital hero from the placeholder to:
  `src="pictures/humaid img.png"`.
  The same commit added `frontend/pictures/humaid img.png`.
- The current commit `d067302` (`Merge remote-tracking branch 'origin/main'`, 2026-10-28 11:59:08 UTC) still contains the `humaid img.png` asset, but its `frontend/digital.html` has the placeholder reference. The diff from `6d4e9f2` to `d067302` shows the exact replacement of the Humaid image line with `pictures/placeholder image.png`, alongside the later navigation/display-settings/content changes.
- The working tree was clean before this report, and `main` matched `origin/main` at `d067302`. The current source therefore reflects the merged branch, rather than an uncommitted local edit hiding the image.

### Deployed response

Read-only requests made to `https://d2mds8vilrvba3.cloudfront.net` returned:

- `GET /`: HTTP 403, `x-cache: Error from cloudfront`, `server: AmazonS3`, `cache-control: no-store`, and the 467-byte CloudFrontSigner auth HTML.
- The response body loads `/js/cfs-handler.js` and says `Redirecting you for Auth`; it does not contain the site page HTML.
- `GET /engineering.html`, `GET /pictures/humaid.jpg`, and `GET /pictures/humaid%20img.png` returned the same HTTP 403 auth response. This is consistent with `docs/deployment.md`, which states that every path except `/js/cfs-handler.js` requires CloudFrontSigner cookies.
- `GET /js/cfs-handler.js` was accessible and returned the CloudFrontSigner handler JavaScript, confirming that the public response is the authentication gate rather than a normal page or image response.

Because no signed CloudFrontSigner cookies were supplied, an authenticated browser/page fetch was not attempted. The deployed response therefore cannot distinguish a deployed 200 image from a deployed missing image behind the auth gate.

## Conclusions

1. **Missing source reference: confirmed.** The current Digital page points to the placeholder and contains no Humaid image reference, while the asset is present and tracked.
2. **Broken relative path or case mismatch: rejected for the current source.** The existing image files are under the expected `frontend/pictures/` directory, and the issue is that the current HTML does not reference either one.
3. **Missing upload or failed deployment: unsupported by repository evidence.** The asset exists in the merge result and `deploy/deploy.sh` copies all of `frontend/.` to the frontend S3 bucket with `aws s3 sync`; there is no build step that would selectively omit this asset. A deployment of the current tree would upload the asset but serve the placeholder because the HTML asks for the placeholder.
4. **CloudFront cache: unlikely as the primary cause.** `deploy/deploy.sh` runs `aws cloudfront create-invalidation --paths "/*"` after the sync. More importantly, the bad image reference is already present in the current merged source. Cache could only matter after the source reference is corrected.
5. **Deployed visual symptom: not directly observable without Midway access.** The public CloudFront response is a 403 authentication page, so the report does not claim to have inspected the authenticated deployed HTML.

## Smallest safe fix

Restore the Digital hero image reference in `frontend/digital.html` to the image added by the latest photo commit:

```html
<img class="homepage-image person-photo person-photo--humaid"
     src="pictures/humaid img.png"
     alt="Humaid working on a laptop">
```

Keep the existing `people-photos.css` link and `.person-photo--humaid` rule. After review, run the repository's normal tests, deploy using the approved credentials and existing `deploy/deploy.sh`, and verify the authenticated Digital page and its image request. Do not delete either tracked Humaid asset until the team confirms which photo is intended.
