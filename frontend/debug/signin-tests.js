// Backend request helper and the "Run sign-in tests" checks for /debug.
// No page code here, so the same file can be run outside a browser.

async function sha256Hex(text) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest)).map(function (b) {
        return b.toString(16).padStart(2, "0");
    }).join("");
}

// Calls the backend and returns { status, body, text, redirected }.
// `body` may be an object (sent as JSON) or a raw string.
async function apiRequest(method, path, body, extraOptions) {
    const options = Object.assign({ method: method, headers: {} }, extraOptions || {});
    if (body !== undefined) {
        options.headers["Content-Type"] = "application/json";
        options.body = typeof body === "string" ? body : JSON.stringify(body);
        // CloudFront signs requests to the Lambda backend and needs the
        // body's SHA-256 hash to do so.
        options.headers["x-amz-content-sha256"] = await sha256Hex(options.body);
    }
    const response = await fetch(path, options);
    const text = await response.text();
    let parsed = null;
    try { parsed = JSON.parse(text); } catch (e) {}
    return {
        status: response.status,
        body: parsed,
        text: text,
        // A browser hides manual redirects as type "opaqueredirect".
        redirected: response.type === "opaqueredirect" || (response.status >= 300 && response.status < 400),
    };
}

// Runs the full sign-in journey with a new synthetic account and reports each
// check through `report(passed, name, detail)`. Returns { passed, failed }.
async function runSignInTests(report) {
    const stamp = Date.now();
    const email = "signin.test." + stamp + "@example.com";
    const password = "synthetic test password " + stamp + "!";
    const wrongPassword = "definitely the wrong password";
    let passed = 0;
    let failed = 0;

    async function check(name, method, path, body, expectStatus, extraCheck, options) {
        let result;
        try {
            result = await apiRequest(method, path, body, options);
        } catch (error) {
            failed += 1;
            report(false, name, "request failed: " + error);
            return null;
        }
        let ok = result.status === expectStatus;
        let detail = "expected HTTP " + expectStatus + ", got "
            + (result.redirected ? "a redirect" : result.status);
        if (ok && extraCheck) {
            const problem = extraCheck(result);
            if (problem) {
                ok = false;
                detail += "; " + problem;
            }
        }
        if (ok) passed += 1; else failed += 1;
        report(ok, name, detail);
        return result;
    }

    function expectError(message) {
        return function (result) {
            return result.body && result.body.error === message ? null : "error message was " + JSON.stringify(result.body && result.body.error);
        };
    }

    // Start signed out, whatever state the browser was in.
    await check("Sign out first", "POST", "/api/logout", undefined, 200);
    await check("My account needs sign-in", "GET", "/api/users/me", undefined, 401,
        expectError("You need to sign in."));

    await check("Sign-up rejects a short password", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email, password: "short1!", accept_terms: true }, 400);
    await check("Sign-up rejects a password with no symbol", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email, password: "no symbol here 123", accept_terms: true }, 400);
    await check("Sign-up rejects a password with no number", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email, password: "no number here!!", accept_terms: true }, 400);
    await check("Sign-up requires accepting the terms", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email, password: password }, 400,
        function (r) { return r.body && r.body.details && r.body.details.indexOf("accept_terms must be true.") !== -1 ? null : "terms error missing"; });
    await check("Sign-up creates the account", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email, password: password, accept_terms: true }, 201,
        function (r) { return r.body && r.body.email === email ? null : "email not returned"; });
    await check("Sign-up rejects the same email (any case)", "POST", "/api/users",
        { full_name: "Sign-in Test", email: email.toUpperCase(), password: password, accept_terms: true }, 409);
    await check("Sign-up signs the user in", "GET", "/api/users/me", undefined, 200,
        function (r) { return r.body && r.body.email === email ? null : "wrong account returned"; });
    await check("My account hides the password hash", "GET", "/api/users/me", undefined, 200,
        function (r) { return r.text.indexOf("password") === -1 ? null : "response mentions password"; });

    await check("Sign out", "POST", "/api/logout", undefined, 200);
    await check("Signed out: my account refused", "GET", "/api/users/me", undefined, 401);

    await check("Sign-in: wrong password refused", "POST", "/api/login",
        { email: email, password: wrongPassword }, 401, expectError("Email or password is incorrect."));
    await check("Sign-in: unknown email gets the same message", "POST", "/api/login",
        { email: "nobody." + stamp + "@example.com", password: password }, 401,
        expectError("Email or password is incorrect."));
    await check("Sign-in: missing password refused", "POST", "/api/login", { email: email }, 400);
    await check("Sign-in: unknown field refused", "POST", "/api/login",
        { email: email, password: password, is_admin: true }, 400);
    await check("Sign-in: Remember me must be true or false", "POST", "/api/login",
        { email: email, password: password, remember_me: "yes" }, 400);
    await check("Sign-in: body that is not a JSON object refused", "POST", "/api/login", "email=x", 400,
        null);
    await check("Sign-in works (email case and spaces ignored)", "POST", "/api/login",
        { email: "  " + email.toUpperCase() + " ", password: password }, 200,
        function (r) { return r.body && r.body.status === "signed_in" ? null : "status was not signed_in"; });
    await check("Signed in: my account works", "GET", "/api/users/me", undefined, 200);

    await check("Sign-in with Remember me works", "POST", "/api/login",
        { email: email, password: password, remember_me: true }, 200);

    await check("Subjects list has five subjects", "GET", "/api/subjects", undefined, 200,
        function (r) { return r.body && r.body.subjects && r.body.subjects.length === 5 ? null : "wrong number of subjects"; });
    await check("Saved items: new account has none", "GET", "/api/users/me/saved", undefined, 200,
        function (r) { return r.body && r.body.items && r.body.items.length === 0 ? null : "list not empty"; });
    await check("Saved items: save a subject", "POST", "/api/users/me/saved", { type: "subject", id: "digital" }, 201);
    await check("Saved items: saving again is harmless", "POST", "/api/users/me/saved", { type: "subject", id: "digital" }, 200);
    await check("Saved items: save a guide", "POST", "/api/users/me/saved", { type: "guide", id: "parents-guide" }, 201);
    await check("Saved items: unknown subject refused", "POST", "/api/users/me/saved", { type: "subject", id: "cooking" }, 400);
    await check("Saved items: list shows both", "GET", "/api/users/me/saved", undefined, 200,
        function (r) { return r.body && r.body.items && r.body.items.length === 2 ? null : "expected 2 items"; });
    await check("Saved items: remove the subject", "POST", "/api/users/me/saved/remove", { type: "subject", id: "digital" }, 200,
        function (r) { return r.body && r.body.items && r.body.items.length === 1 ? null : "expected 1 item left"; });

    await check("Content list shows signed in", "GET", "/api/content", undefined, 200,
        function (r) { return r.body && r.body.signed_in === true ? null : "signed_in was not true"; });
    const content = await apiRequest("GET", "/api/content");
    const membersItem = content.body && content.body.items
        ? content.body.items.find(function (item) { return item.requires_login; })
        : null;
    if (membersItem) {
        const download = await apiRequest("GET", membersItem.download_url, undefined, { redirect: "manual" });
        const ok = download.redirected;
        if (ok) passed += 1; else failed += 1;
        report(ok, "Signed in: members-only download allowed",
            ok ? "redirected to a signed download link" : "expected a redirect, got HTTP " + download.status);
    }

    for (let attempt = 1; attempt <= 5; attempt += 1) {
        await check("Lockout: wrong password " + attempt + " of 5", "POST", "/api/login",
            { email: email, password: wrongPassword }, 401);
    }
    await check("Lockout: correct password now refused", "POST", "/api/login",
        { email: email, password: password }, 429);
    await check("Lockout: existing session still works", "GET", "/api/users/me", undefined, 200);

    await check("Delete account: wrong password refused", "POST", "/api/users/me/delete",
        { password: wrongPassword }, 400, expectError("Password is incorrect."));
    await check("Delete account", "POST", "/api/users/me/delete", { password: password }, 200);
    await check("Deleted: my account refused", "GET", "/api/users/me", undefined, 401);
    await check("Deleted: saved items refused", "GET", "/api/users/me/saved", undefined, 401);
    await check("Deleted: sign-in refused", "POST", "/api/login",
        { email: email, password: password }, 401);
    if (membersItem) {
        await check("Signed out: members-only download refused", "GET", membersItem.download_url, undefined, 401,
            null, { redirect: "manual" });
    }

    return { passed: passed, failed: failed };
}

if (typeof module !== "undefined") {
    module.exports = { apiRequest: apiRequest, runSignInTests: runSignInTests };
}
