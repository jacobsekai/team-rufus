// Shared helper for calling the backend API (see docs/api.md).
//
// The site and API share one address, so paths are relative ("/api/...")
// and the browser sends the session cookie automatically.
// CloudFront signs requests to the Lambda backend, so every request with a
// body must also send the body's SHA-256 hash in x-amz-content-sha256.

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest))
    .map(function (b) { return b.toString(16).padStart(2, "0"); })
    .join("");
}

// Returns { status, body, retryAfter }. body is the parsed JSON, or null
// when the response is not JSON (CloudFront's HTML 403 page when the Midway
// sign-in has expired). Network failures reject, so callers use try/catch.
async function apiRequest(method, path, body) {
  const options = { method: method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers["Content-Type"] = "application/json";
    options.headers["x-amz-content-sha256"] = await sha256Hex(options.body);
  }
  const response = await fetch(path, options);
  let parsed = null;
  try { parsed = await response.json(); } catch (e) { /* not JSON */ }
  return {
    status: response.status,
    body: parsed,
    retryAfter: Number(response.headers.get("Retry-After")) || 0,
  };
}

// Plain-language message for a failed request that is not about what the
// user typed (each page handles its own "wrong details" cases).
function apiProblemMessage(result) {
  if (result && result.status === 403) {
    return "Your Midway sign-in has expired. Reload the page and try again.";
  }
  return "Something went wrong on our side. Please try again in a few minutes.";
}
