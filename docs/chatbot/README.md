# Chat assistant (Task 4 AI feature)

The site's AI feature is a custom chat agent in **Amazon's internal Amazon
Quick** (account `amazonbi`). Every page shows an **Ask about T Levels**
button that opens the agent in a new tab. Visitors are Amazon staff (the
site is behind Midway), and they sign in to Quick with Midway too.

## Why a button and not a chat window inside the page

Amazon's internal Quick only allows embedding on an allow-listed domain. The
[iframe embedding runbook](https://w.amazon.com/bin/view/Qinternal/Runbooks/quick-suite-iframe-embedding-enablement-process/)
requires an Amazon-owned domain (for example `*.amazon.dev`), a completed
AppSec review, and 5 to 10 business days. The prototype's
`d*.cloudfront.net` address is not Amazon-owned and has no AppSec review, so
the agent opens in its own tab instead. Embedding is listed as future work.

## Files

| File | Purpose |
|---|---|
| `knowledge/*.md` | Upload to the Quick space. The agent answers only from these. |
| `agent-instructions.md` | Paste into the chat agent builder: scope, safety rules, tone, welcome message, suggested prompts. |
| `test-prompts.md` | 17 test prompts with expected behaviour, and a table to record results. |
| `frontend/chat/config.js` | Set `agentUrl` to the agent's share link. |
| `frontend/chat/chat-launcher.js` | Adds the button. Include both scripts on every page (see the comment at the top). |

## Setting it up in Amazon Quick

1. **Sign in.** Open Amazon Quick, use the account name `amazonbi`, and sign
   in with Midway. If you don't see **Chat agents** and **Spaces** in the left
   navigation, request a Pro role (Reader Pro or Author Pro).
2. **Create the space.** Spaces > Create space > name it
   "T Levels at Amazon" > upload the three files in `knowledge/`.
3. **Create the agent.** Chat agents > Create chat agent > Skip (builder
   view). Fill in each field from `agent-instructions.md`. Under
   **Knowledge sources**, link the "T Levels at Amazon" space.
   This step matters: an agent with no linked space answers from everything
   the *visitor* can access in Quick, which could include their own internal
   documents.
4. **Test.** Use the preview to run every prompt in `test-prompts.md` and
   record the results. Adjust the instructions and re-test until they pass.
5. **Launch and share.** Launch chat agent > Share > add the team members
   and assessors as **Viewer**. Ask one assessor to open it to confirm they
   have access.
6. **Connect the site.** Copy the agent's link into `agentUrl` in
   `frontend/chat/config.js`, then run `deploy/deploy.sh`.

## Inputs for the Task 4 feasibility assessment

- **Technical requirements:** Amazon Quick with chat agent permissions; one
  space holding the knowledge files; Midway sign-in. No backend code or API
  keys in this repository; the site only links to the agent.
- **Data requirements:** the knowledge files contain public information only
  (TLevels.gov.uk, UCAS, aboutamazon.co.uk, the brief, the site's own help).
  The agent is told not to ask for personal details. Conversations are held
  in Amazon's internal Quick, not in this project's database.
- **Ethical considerations:** the users may be 16 to 19, so the agent is
  limited to T Level topics, refers wellbeing concerns to Childline and
  trusted adults, never promises placements, and won't write applications.
  Answers can still be wrong, so it cites sources and points to official
  sites.
- **AI-generated vs human-generated data:** the agent writes new sentences
  from the human-written knowledge files. It can sound confident when it is
  wrong, it doesn't know anything after the files were last updated, and two
  people asking the same question can get differently worded answers.
- **Limitations:** only Amazon staff can use it (internal Quick + Midway);
  it opens in a new tab rather than on the page; the knowledge files must be
  updated by hand when facts change.
