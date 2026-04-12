# Requirements

## Overview

Exetasi is a free, open-source quiz and exam web application that allows individuals and organizations to publish and take quizzes and exams online.

### Technology Stack

- **Frontend**: [Quasar](https://quasar.dev/) (Vue 3 / TypeScript), Single Page Application (SPA)
- **Mobile**: [Capacitor](https://capacitorjs.com/) wrapper for iOS and Android
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: PostgreSQL

### Goals

- Free to use with no paywalls
- Minimal hosting cost; preference for free tiers and pay-as-you-go pricing
- Responsive and accessible across all devices (WCAG 2.1 AA minimum, AAA where practical without excessive maintenance burden)
- No hard dependency on any single cloud provider; deployable on Vercel, AWS, GCP, Hetzner, and Supabase

---

## Users

A user has:

- A **username** (displayed in the UI; globally unique across all users; can be changed at any time)
- An immutable internal **ID** (used for all references so username changes do not break existing records)
- A brief **bio**
- A personal **avatar icon**

On registration, a **personal organization** is automatically created for the user. All exams — whether created by an individual or a team — live inside an organization.

### Authentication

Users can sign in using OAuth 2.0 with:

- Google
- GitLab
- GitHub

Multiple OAuth providers can be linked to a single account, allowing the user to sign in with any of them.

### Account Deletion

A user can delete their account. On deletion:

- All exam **attempts** taken by the user are permanently deleted
- Exams, organizations, and other content **owned** by the user are not deleted; ownership is retained under the user's now-deleted account record so the data remains accessible to other organization members

---

## Organizations

Every user has a **personal organization** created automatically on registration. Additional organizations can be created for teams. An organization has:

- A **name**
- A **URL slug** (used in shareable links)
- A **description**
- An **avatar**

Members are added by username (no email invitations). A user can belong to multiple organizations. An organization can have multiple Owners; at least one Owner must exist at all times.

### Personal Organization

The personal organization's name and URL slug are derived from the user's username and update automatically when the username changes. The UI displays a **warning** when creating an exam inside a personal organization, noting that the organization's URL slug will change if the username is changed — which would break any previously shared exam links using that slug.

### Roles

| Role       | Permissions |
| ---------- | ----------- |
| **Owner**  | Full control: create, edit, archive exams; add, remove, and change the role of any member; view analytics; export results |
| **Editor** | Create and edit exams, view analytics, export results |
| **Grader** | Grade open-ended and fill-in-the-blank answers, view results and analytics, export results |
| **Viewer** | View exam details, results, and analytics; export results; suggest improvements |

Only Owners can manage membership.

### Leaving and Deletion

A user can **voluntarily leave** any organization they belong to, unless they are the sole Owner — in that case, they must either promote another member to Owner or delete the organization first. The UI shows a warning before confirming.

An organization can be **deleted** by its Owner. Deletion is permanent and removes all exams, versions, sections, questions, answers, attempt records, and audit log entries belonging to that organization. The UI requires explicit confirmation and displays a summary of what will be deleted (number of exams, total attempts) before proceeding. This action cannot be undone.

When a user deletes their account and they are the sole Owner of any organizations, those organizations and all their data are also deleted. The account deletion flow shows a list of affected organizations and requires explicit confirmation for each.

### Exam Visibility

Exams within an organization can be:

- **Public**: anyone with the exam ID or URL can take it
- **Restricted**: only users on an explicit allowlist can take it

For restricted exams, Owners and Editors manage the allowlist by adding or removing usernames. A user not on the allowlist who attempts to access the exam receives an "access denied" response.

---

## Exam

An exam has:

- An **ID**
- A **name**
- A **public description** (visible to all)
- A **private description** (visible to organization members only — Viewers and above)
- An **owner** (user or organization that created it)

### Lifecycle

Exams and versions cannot be deleted. Instead, an exam can be **archived**: it remains visible to organization members and all past attempt data is preserved, but it can no longer be taken. Archiving can be reversed by an Owner or Editor.

### Sharing

- Exams are shared via their **ID or URL**
- Owners and Editors can generate a **QR code** for easy sharing

### PDF Certificate

If configured, users can download a PDF certificate upon exam completion. Configuration per exam includes:

- Uploading an **image template** (e.g., a branded background)
- Placing **fields** — username, exam ID, exam-taking instance ID, and score — using a **visual drag-and-drop editor**
- Field positions can also be set or adjusted by entering **pixel coordinates** manually

The certificate uses the test-taker's **username** as the name field. The UI displays a note where the username is configured reminding exam creators that this is the name that will appear on certificates, so test-takers should be advised to set an appropriate username before taking a formal exam.

There is a single active certificate template per exam. If the template is updated, all subsequently generated certificates (including for past attempts) use the new template.

### Import / Export

Exams (including all versions, sections, and questions) can be exported and imported in:

- **JSON**
- **TOML**
- **YAML**

Individual questions can also be imported from another exam or version that the user owns.

Exported files contain the exam structure only — image references (URLs or paths) are included but the image files themselves are not bundled. When importing on a different instance, images referenced by URL will continue to resolve; images stored on local disk or object storage will need to be re-uploaded manually.

### Media Storage

Uploaded images (question images, answer option images, and certificate templates) are stored in a configurable backend:

| Backend | Notes |
|---------|-------|
| **Local disk** | Default for self-hosted deployments |
| **Amazon S3** | AWS-hosted deployments |
| **Google Cloud Storage (GCS)** | GCP-hosted deployments |
| **Cloudflare R2** | S3-compatible; no egress fees |
| **External URL** | Reference an image hosted elsewhere; not uploaded to the app |

The storage backend is set at the instance level via configuration. All backends expose the same internal interface so the rest of the application is storage-agnostic.

**File limits** (configurable per instance):
- Maximum **file size** (e.g., 5 MB by default)
- Maximum **pixel dimensions** (width × height; e.g., 4000 × 4000 px by default)

### Data Retention

Attempt records (answers, scores, event logs) are kept **indefinitely** by default.

Owners can **bulk-delete attempt results** for a specific exam version up to a chosen cutoff date. This permanently removes the attempt data for that version up to and including the cutoff; no undo is available. The exam structure (questions, answers, configuration) is unaffected.

---

## Versions

An exam always has exactly **one active version**. Activating a version automatically deactivates the previously active one. The first version of a new exam is created empty and becomes active immediately. For subsequent versions, the user selects a previous version to copy all its sections and questions from; the new version does not become active until explicitly activated.

An active version can be **empty** (no sections or questions), in which case the exam exists but test-takers would see an empty exam. This is expected during initial setup.

Each version has:
- A **name** (e.g., "Spring 2026", "Final Revision")
- A **public description** (visible to test-takers)
- A **private description** (visible to organization members only)

### Configuration

| Setting                                   | Description                                                                  |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| Full exam time limit                      | Maximum duration for the entire exam                                         |
| Show remaining time                       | Whether the countdown timer is visible during the exam                       |
| Allow pauses                              | Pausing stops the timer but hides all questions until resumed                |
| Show answer and score after each question | Immediate per-question feedback mode; once the correct answer is shown the response is locked and cannot be changed |
| Show progress                             | Display number of answered questions and current running score               |
| Show final result                         | Whether the final score is displayed at the end                              |
| PDF certificate                           | Whether a certificate can be downloaded at the end                           |
| Approval score                            | Minimum score to pass, expressed as either a **percentage** (e.g., 70%) or a **raw point value**; optionally shows "Approved / Not Approved" at the end |
| Allow navigation to previous questions    | Whether the user can go back to earlier questions                            |
| Randomize section order                   | Shuffle section order on each attempt                                        |
| Randomize question order                  | Shuffle question order within each section on each attempt                   |
| Randomize answer order                    | Shuffle answer options within each question on each attempt                  |
| Default question score                    | Default point value applied to all questions                                 |
| Allow question flagging                   | Whether users can flag a question to review before submitting                |
| Allow retakes                             | Whether the same user can take the exam more than once                       |

---

## Sections

A version has one or more **sections**. Each section has:

- An **ID**
- A **name** (short label shown in the UI)
- A **public description**
- A **private description**

Sections can be manually reordered by Editors and above. This base order is used when section randomization is disabled, and as the starting point when it is enabled.

The following version-level settings can be overridden at the section level where they are meaningful: time limit, show remaining time, allow pauses, show answer and score after each question, show progress, allow navigation to previous questions, randomize question order, randomize answer order, default question score, and allow question flagging. Settings that govern the exam as a whole — such as allow retakes, PDF certificate, approval score, show final result, and randomize section order — cannot be overridden at the section level.

Sections also have their own exclusive settings:

| Setting                     | Description                                                                         |
| --------------------------- | ----------------------------------------------------------------------------------- |
| Scored                      | Whether answers in this section count toward the total score                        |
| Count toward time limit     | Whether time spent here counts against the exam timer                               |
| Questions to draw from pool | How many questions to randomly select from this section's question pool per attempt. Must be between 1 and the pool size (inclusive); validated when saving. If not set, all questions in the pool are used. |

---

## Questions

A section contains one or more **questions** in its pool. Each question has:

- An **ID**
- A **private description** (notes for editors and graders, not shown to test-takers)
- One or more **question phrasings** (minimum one) — the phrasing shown to the user is randomly selected per attempt and the selected phrasing ID is recorded in the attempt record. Phrasings are written in **Markdown**. For fill-in-the-blank questions, each phrasing defines its own set of blanks independently.
- An optional **image** (subject to the configured file size and pixel limits)
- A **question type** (see below)
- A **point value** (defaults to the version-level default question score)

Questions can be manually reordered within a section by Editors and above. This base order is used when question randomization is disabled. Questions can also be **moved between sections** within the same version by Editors and above.

The following section-level settings can be overridden at the question level where meaningful: show answer and score after each question, randomize answer order, point value, allow question flagging, scored, and count toward time limit. Settings that govern a group of questions — such as questions to draw from pool, time limit, allow pauses, show progress, and allow navigation — cannot be overridden at the question level.

### Question Types

#### 1. Multiple Choice

The user selects one or more answers from a list of options.

- **Correct answers**: one or more options, each with a percentage weight
  - If one option has 100%: single-choice question
  - If multiple options share percentages summing to 100%: multi-choice question
- **Incorrect answer pool**: a set of wrong options from which answers are randomly drawn to fill up to "total options to show"
- **Total options to show**: configured per question — the incorrect answer pool must contain at least `total_options_to_show − number_of_correct_answers` options; this is validated when saving the question
- **Penalty for wrong answers** (multi-choice only): configured per question
  - **No penalty**: selecting an incorrect option adds nothing to the score
  - **Negative scoring**: each selected incorrect option subtracts its percentage weight from the score; the final question score is clamped to a minimum of zero

#### 2. Open-Ended

The user writes a free-text response. Graded manually by a Grader, Editor, or Owner. Each open-ended question has a configurable **character limit** (default: 255 characters); the UI enforces this limit while the test-taker types.

#### 3. Fill-in-the-Blank

The question phrasing (Markdown) contains one or more inline blanks, marked with the syntax `{{n}}` where `n` is the blank number (e.g., `The capital of France is {{1}} and its currency is {{2}}`). Each phrasing defines its own blanks independently.

Each blank is graded independently using one of:

- **Exact match** (case-insensitive, whitespace-trimmed)
- **Regex pattern** (Python `re` module syntax, validated when saving)
- **Manual grading** by a Grader, Editor, or Owner

Each blank also has an individual **point weight** (the question's total point value is distributed across blanks according to their weights).

#### 4. Drag-and-Drop Ordering

The user arranges a set of items into the correct sequence.

Scoring mode is configured per question:

- **All-or-nothing**: full points only if the entire sequence is correct
- **Partial credit**: `(correctly placed items / total items) × question points`

#### 5. Matching

The user pairs items from two columns.

Scoring mode is configured per question:

- **All-or-nothing**: full points only if all pairs are correct
- **Partial credit**: `(correctly matched pairs / total pairs) × question points`

#### 6. Informational

No answer required. The user reads the content and advances. Does not affect the score or time limit (unless overridden).

---

## Answers

### Multiple Choice

Each option (correct or incorrect) has:
- **Text** (Markdown)
- An optional **image**

Correct options also carry a **percentage weight** used for scoring. Incorrect options belong to the **incorrect answer pool** and are randomly drawn per attempt.

### Fill-in-the-Blank

Each blank (referenced by its `{{n}}` number in the phrasing) has:
- One or more **accepted values** — for exact match and regex modes, multiple accepted values can be defined (any match is correct)
- A **grading mode**: exact match, regex, or manual
- A **point weight** — blanks within a question can carry different weights; the question's total point value is distributed proportionally across blank weights

### Open-Ended

No predefined answers. The test-taker writes a free-text response and a Grader, Editor, or Owner assigns the score.

### Drag-and-Drop Ordering

Each **item** to be ordered has:
- **Text** (Markdown)
- An optional **image**

The correct sequence is defined by the order items are saved in the editor.

### Matching

Each **pair** consists of:
- A **left item** (Markdown text + optional image)
- A **right item** (Markdown text + optional image)

The correct answer is the defined left↔right mapping. Each left item maps to exactly one right item (strictly one-to-one). The right-side items are shuffled before presentation.

Optionally, **distractor right items** can be added — extra right-side items that do not correspond to any left item, preventing elimination-based guessing. Distractors are not mandatory. For scoring purposes, "total pairs" refers to the number of left items only; distractors do not affect the denominator.

---

## Exam Taking

An account is required to take any exam (no anonymous/guest attempts).

When a user starts an exam, the system creates an attempt record containing:

- The **user**
- The **exam version** active at the time the attempt was started
- **Start and end timestamps** (server-side)
- A **per-question event log**: when each question was first viewed, answered, and last modified
- A **per-question flag state**: the user can flag any question during the attempt to mark it for review before submitting; this is an attempt-level state, not a property of the question definition
- A unique **exam-taking instance ID**

### Progress and Resumption

Answers and event log entries are saved continuously as the user progresses. If the user loses connection or closes the browser mid-exam, they can resume the attempt from where they left off. The timer resumes from the elapsed time recorded at the last save.

### Version Changes

If the active version of an exam changes while a user has an attempt in progress, that attempt continues on the version it started on and is unaffected by the change.

### Time Limit

When the time limit expires, the exam **auto-submits** with whatever answers have been given up to that point.

### Completion

At the end of the exam (subject to configuration):

- The **final score and result** are displayed alongside the **maximum possible score**
- If any questions require manual grading, the score is shown as **pending** until all such questions have been graded
- A **PDF certificate** can be downloaded once the final score is confirmed, embedding the user's name, exam ID, instance ID, and score

### Review Screen

If the version has both "Allow navigation to previous questions" and "Allow question flagging" enabled, a **review screen** is shown before final submission. It lists all questions with their answered/unanswered status and any flags, and allows the test-taker to navigate back to any question before committing.

### Attempt History

Test-takers can view a **personal history page** listing all their past exam attempts. Each entry shows the exam name and version name **as they were at the time of the attempt** (name changes after submission do not retroactively affect this display), along with the submission timestamp, score, and pass/fail result (where configured). Attempts with a pending score are shown as pending.

### Retake Override

Exam Owners and Editors can manually grant a specific user permission to retake an exam, regardless of the exam's retake setting.

---

## Analytics

Available to all roles: Owner, Editor, Grader, and Viewer.

All analytics views support **date range filtering** to scope metrics to a specific period (e.g., last 30 days, custom range).

### Per-Version Metrics

The following metrics are available scoped to a single exam version:

- **Average score** across all attempts
- **Pass rate** (if an approval score is configured)
- **Score distribution** (histogram)
- **Per-question difficulty**: for auto-graded questions, the percentage of users who answered correctly; for manually graded questions, the average score as a percentage of the question's point value
- **Average time per question**
- **Per-option selection breakdown** (multiple choice): for each question, shows how many test-takers selected each answer option (correct and incorrect). Useful for identifying confusing or poorly written distractors.

### Cross-Version Comparison

Versions of the same exam can be compared side by side on any per-version metric (e.g., average score across v1 vs. v2).

Some metrics are also aggregated across **all versions** of an exam where meaningful, for example:

- **Overall pass rate** across all versions and attempts
- **Total number of attempts** across all versions

### Export

All roles can export the full attempt dataset — results, per-question timestamps, and scores — in CSV or JSON format.

---

## Scoring

### Question Score

Each question has a **point value** (set per question, defaulting to the version-level default).

- **Multiple choice (single correct)**: full points if the correct answer is selected; zero otherwise
- **Multiple choice (multiple correct)**: `sum of selected correct answer percentages × question points`; if **penalty for wrong answers** is enabled, each selected incorrect option subtracts its percentage weight — final score clamped to zero
- **Open-ended / Fill-in-the-blank (manual)**: grader assigns a score between 0 and the question's point value
- **Fill-in-the-blank (auto)**: each blank earns `(blank weight / total blank weights) × question points`; a mixed question (some blanks auto, some manual) scores the auto blanks immediately and holds the manual blanks as pending
- **Drag-and-drop ordering (all-or-nothing)**: full points or zero
- **Drag-and-drop ordering (partial)**: `(correctly placed items / total items) × question points`
- **Matching (all-or-nothing)**: full points or zero
- **Matching (partial)**: `(correctly matched pairs / total pairs) × question points`

### Exam Score

The exam score is the sum of all scored question scores across all scored sections. The **maximum possible score** is the sum of point values for all scored questions drawn for that attempt. Both the achieved score and the maximum are displayed to the user at the end of the exam.

For a **percentage-based approval score**, the pass threshold is calculated as `approval_percentage × maximum_possible_score` for that attempt. This means the threshold adjusts when different questions are drawn from a pool across attempts.

---

## Grading Queue

Owners, Editors, and Graders see a **grading queue** when they log in: a list of exam attempts that contain at least one manually graded question (open-ended or manual fill-in-the-blank) that has not yet been graded.

The queue can be **filtered** by exam and by date range, and **sorted** by submission timestamp (ascending or descending) or by number of pending questions. Each entry shows:

- Exam name and version
- Test-taker username
- Submission timestamp
- Number of pending (ungraded) questions

Selecting an entry **locks the attempt** for that grader: it is removed from the queue for all other graders to prevent concurrent grading conflicts. The lock is released when the grader navigates away from the grading view, or automatically after a configurable idle timeout — whichever comes first. Saving partial progress does not extend or hold the lock beyond the idle timeout.

In the **grading view**, the grader sees each question, the test-taker's response, an input to assign a score between 0 and the question's point value, and an optional **written feedback field**. Feedback for each question is saved and made visible to the test-taker **immediately** when that question's grade is saved — the test-taker does not need to wait for the full attempt to be graded. Progress can be saved at any point without completing all questions. Once all questions in an attempt are graded, the attempt is marked complete and the final score is calculated and made visible to the test-taker.

---

## Notifications

The application delivers **in-app notifications** (no email). Notifications appear in a notification centre within the UI.

| Event | Recipient |
|-------|-----------|
| A manually graded question in your attempt has been scored | Test-taker |
| Your attempt has been fully graded and the final score is available | Test-taker |
| An attempt requiring manual grading has been submitted in an exam you own or have Grader access to | Owner, Editor, Grader |

Notifications are marked as read when viewed. No push notifications to mobile devices in the initial release.

---

## Audit Log

A tamper-evident audit log records significant actions across the application. The log is accessible to Owners of the relevant organization.

Logged events include:

| Category | Events |
|----------|--------|
| **Exam** | Created, archived, unarchived, exported, imported; name or description changed |
| **Version** | Created, activated; configuration changed (old and new values recorded); name or description changed |
| **Section** | Created, reordered; name, description, or configuration changed |
| **Question** | Created, moved between sections, reordered; phrasing, image, type, point value, or configuration changed |
| **Answer** | Option added, removed, or edited (text, image, weight) |
| **Attempt results** | Bulk deletion performed (by whom, version, cutoff date, record count) |
| **Grading** | Score assigned or updated for a question (grader, attempt, question, old and new score) |
| **Membership** | Member added, removed, or role changed (by whom, affected user, old and new role); restricted exam allowlist modified |
| **Account** | User account deleted |
| **Media** | Storage backend configuration changed |

Each log entry records the acting user's ID, the timestamp, and the relevant entity IDs.

The audit log can be **exported** by Owners in TSV, CSV, or JSON format, optionally filtered by date range or event category.

---

## Non-Functional Requirements

### Accessibility

- **WCAG 2.1 Level AA** as a baseline for all features
- **WCAG 2.1 Level AAA** where it can be achieved without disproportionate implementation or maintenance cost

### Responsiveness

- Fully responsive across mobile, tablet, and desktop
- Tested on current versions of Chrome, Firefox, Safari, and Edge

### Performance

- Exam-taking interactions must be low-latency (no noticeable lag on question navigation or answer submission)
- Analytics queries must be optimized for exams with large numbers of attempts

### Security

- All API endpoints require authentication and enforce role-based authorization
- Secrets and database credentials are stored in environment variables; none are hardcoded
- OAuth flows use PKCE where supported
- API rate limiting is applied to all endpoints to prevent abuse; limits are configurable per instance

### Session Management

User sessions expire after **1 week of inactivity** and are extended automatically on each authenticated request (sliding window refresh token). This is appropriate for a non-financial community app where the priority is avoiding mid-exam session expiry.

During active exam taking, the client refreshes the session token silently in the background to prevent any possibility of the session expiring while an attempt is in progress.

### Internationalisation

Multi-language support and right-to-left script layouts are **out of scope** for the initial release but should be considered when structuring UI text (e.g., using string keys rather than hardcoded copy) to ease a future migration.

### Portability and Deployment

The application is designed to run on any standard infrastructure. Deployment guides are provided for:

| Platform     | Notes                                                   |
| ------------ | ------------------------------------------------------- |
| **Vercel**   | Frontend SPA + serverless FastAPI backend               |
| **AWS**      | EC2 / ECS for backend, RDS for PostgreSQL               |
| **GCP**      | Cloud Run for backend, Cloud SQL for PostgreSQL         |
| **Hetzner**  | VPS with Docker Compose (frontend + backend + database) |
| **Supabase** | PostgreSQL database + optional Auth                     |
