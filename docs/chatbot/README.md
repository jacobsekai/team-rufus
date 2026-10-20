# Chat assistant (Task 4 AI feature)

Every page has an **Ask about T Levels** button that opens a chat panel on
the same page. Questions go to `POST /api/chat`, which answers with
**Claude Opus 5.5 on Amazon Bedrock**, checked by a **Bedrock Guardrail**.
The site is behind Midway, so only Amazon staff can use it.

## Why Bedrock and not Amazon Quick

The team first chose Amazon Quick. Embedding a Quick chat agent inside the
site needs an Amazon-owned domain, an AppSec review, and an allow-listing
ticket ([runbook](https://w.amazon.com/bin/view/Qinternal/Runbooks/quick-suite-iframe-embedding-enablement-process/)),
which takes weeks; the prototype's `cloudfront.net` address qualifies for
none of these. Calling Claude through Bedrock from our own backend keeps the
chat on the page, works for every Midway visitor with no extra sign-in, and
lets us control the safety rules in code. Embedding Quick is future work.

## How a question is answered

1. **Guardrail (input).** Harmful content (sexual, violence, hate, insults,
   misconduct) and prompt attacks are blocked at the strictest level. Email
   addresses, phone numbers, postal addresses and UK NI and NHS numbers are
   masked (for example `{EMAIL}`), so they never reach the model. Card numbers
   and passwords block the message. A blocked question gets a reply that
   signposts Childline (0800 1111) and 999, in case the user needs help.
2. **Claude.** The system prompt is `backend/chatbot/instructions.md`
   followed by every file in `backend/chatbot/knowledge/`. It limits answers
   to T Levels, placements and the website, and sets rules for a 16 to 19
   audience (no personal data, no promises, no writing applications,
   wellbeing signposting, resisting attempts to change the rules). Effort is
   `low` for fast, short answers. The system prompt is cached, so repeat
   requests cost less.
3. **Guardrail (output).** The answer is checked again before it is shown.

The server stores no conversation and never logs message text; it logs only
token counts and the stop reason. The browser keeps the conversation in
memory and drops it when the page closes. Only normal answers are kept in the
history, so a blocked question is never sent again.

## Files

| File | Purpose |
|---|---|
| `backend/chat.py` | The endpoint, request validation, guardrail and Claude calls |
| `backend/chatbot/instructions.md` | Rules and style for the assistant |
| `backend/chatbot/knowledge/*.md` | What the assistant knows, with sources |
| `frontend/chat/chat-widget.js` | The chat button and panel (one script tag per page) |
| `deploy/template.yaml` | `ChatGuardrail` and the Lambda permissions |
| `test-prompts.md` | 17 test prompts with expected behaviour |

To change what the assistant knows, edit the knowledge files and redeploy.
To change the guardrail, edit `ChatGuardrail` and also the `Description` of
`ChatGuardrailVersion`, so a new version is published.

## API

`POST /api/chat` with the recent conversation, oldest first, alternating
user and assistant and ending with the user's question:

```json
{"messages": [{"role": "user", "content": "What is a T Level?"}]}
```

| Status | Body |
|---|---|
| `200` | `{"status": "answered", "reply": "..."}`, or `"blocked"` / `"refused"` with a safe reply |
| `400` | Invalid messages (max 20 messages; questions 1 to 1,000 characters; 12,000 characters in total) |
| `503` | The assistant is unavailable (or the guardrail is not configured) |

## Inputs for the Task 4 feasibility assessment

- **Technical requirements:** Amazon Bedrock access to Claude Opus 5.5 in
  us-west-2; a Bedrock Guardrail; the Lambda role allowed
  `bedrock-mantle:CreateInference` and `bedrock:ApplyGuardrail` only; Python
  3.12 with the Anthropic SDK. No API keys: the Lambda's IAM role signs every
  request.
- **Data requirements:** the knowledge files contain public information only
  (TLevels.gov.uk, UCAS, aboutamazon.co.uk, the brief, the site's own help).
  Personal details are masked before the model sees them, and nothing is
  stored.
- **Ethical considerations:** the audience includes 16 to 19 year olds, so
  the guardrail runs at its strictest, blocked questions signpost help, and
  the assistant never promises placements or writes applications. It can
  still be wrong, so it cites sources and the panel says so.
- **AI-generated vs human-generated data:** the assistant writes new
  sentences from the human-written knowledge files. It can sound confident
  when it is wrong, it knows nothing newer than the files, and the same
  question can get differently worded answers.
- **Cost:** Claude Opus 5.5 with a cached system prompt costs well under a
  penny per question at prototype traffic; guardrail checks cost fractions of
  a penny.
- **Limitations:** only Amazon staff can use it (Midway); no per-person rate
  limit; the knowledge files must be updated by hand when facts change.
