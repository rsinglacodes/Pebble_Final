Pebble --- AI-Based DSA Learning and Video Generation Platform
Project name: Pebble  
Working tagline: Your little companion for understanding algorithms  
Document: Project overview, product workflow, frontend plan,
architecture, security, and implementation blueprint  
Status: Proposed system design
---
1. Executive Overview
Pebble is an AI-powered DSA learning platform that helps students
understand coding problems, algorithms, and solutions through
personalized explanations, multilingual code support, execution-based
visualization, and narrated educational videos.
Students can enter a LeetCode problem, describe an algorithm they want
to learn, or paste their own solution. Pebble determines the learning
intent, retrieves an existing solution when available, generates a
solution when necessary, validates code, captures execution states, and
uses those states to create an educational animation.
The platform combines:
User authentication and onboarding.
A conversational learning workspace.
Problem and solution retrieval.
RAG over an approved GitHub solution corpus.
AI solution generation and repair.
Isolated code execution and testing.
Execution traces for reliable visualizations.
Manim animation.
Azure AI Speech narration.
FFmpeg video/audio assembly.
Cloudflare R2 storage and video reuse.
NeonDB for structured application data.
Product principle
Pebble should teach the reasoning behind a solution---not merely
return code or a video.
The LLM is responsible for reasoning, explanation, and structured scene
planning. Code execution is responsible for actual program states. Manim
is responsible for rendering those states. This separation reduces the
risk of an AI inventing a dry run that does not match the code.
---
2. Problem Statement
DSA learners commonly use separate platforms for problem statements,
solution repositories, explanations, code editors, dry runs, and videos.
A student may find a problem on LeetCode, search GitHub for a solution,
watch a YouTube explanation, and manually trace the code.
This creates several problems:
Fragmented learning: The student must switch between multiple
resources.
Solution without understanding: Code may be available without a
clear explanation of why it works.
Language mismatch: A solution may be written in a language the
student is not currently learning.
Difficult execution tracing: Beginners may struggle to track
pointers, variables, recursion, and data-structure changes.
Repeated video generation: The same educational content may be
generated repeatedly when it could be reused.
Unverified code: A retrieved or AI-generated solution may
contain errors or fail edge cases.
Formal problem statement
> Design and develop a secure, AI-powered DSA learning platform that
> accepts a coding problem, algorithm concept, or user-submitted
> solution; retrieves or
> generates code; validates code through isolated execution; derives
> visualizations from execution traces; and produces reusable narrated
> educational videos.
---
3. Target Users
Primary audience
College students and coding-interview aspirants who are learning DSA or
preparing for technical assessments.
Secondary audience
Beginners learning algorithms after programming fundamentals.
Students who understand syntax but struggle with problem-solving.
Intermediate learners revising interview questions.
Students who want explanations in English or Hindi.
Students who prefer visual explanations over text-only tutorials.
User needs
Users should be able to:
Search for a problem by LeetCode ID, title, or description.
Learn an algorithm from scratch.
Paste their own code and understand it.
Select Java, C++, Python, JavaScript, or another supported language.
Select English or Hindi narration/explanation.
Ask follow-up questions.
View a dry run based on actual execution.
Watch an educational video.
Save their progress and revisit previous learning.
---
4. Product Scope and Learning Modes
All modes share a common backend pipeline after the input has been
interpreted.
Mode A --- Learn an Algorithm
The user asks to learn a concept, for example Binary Search, BFS,
Sliding Window, or Dynamic Programming.
Pebble should provide:
Prerequisites and intuition.
Problem-solving use cases.
Core steps.
Pseudocode.
Example.
Complexity.
Code in the selected language.
Execution trace and visualization.
Educational video.
For a concept without one specific problem, the system can use a
controlled canonical example to demonstrate the algorithm.
Mode B --- Explain My Solution
The user pastes code and selects the language.
Pebble should:
Identify the language and validate the input.
Ask for the problem statement or problem ID if needed.
Explain the user's code without replacing it unnecessarily.
Identify important variables, conditions, loops, and data
structures.
Execute the code in an isolated environment when supported.
Capture an execution trace.
Explain issues or possible improvements.
Generate a visualization and video if requested.
The user's original code must be preserved separately from any suggested
correction.
Mode C --- Find or Generate a Solution
The user enters a LeetCode ID, URL, title, or problem statement.
Pebble should:
Resolve the problem identity.
Search the solution repository for the matching problem and
language.
Retrieve a suitable solution if available.
Verify source and language.
Validate retrieved code.
If no suitable solution exists, generate code with an LLM.
Test the code.
Attempt limited repairs if tests fail.
Explain the validated solution.
Generate the execution visualization and video.
Shared pipeline
``` text
Learn an Algorithm ───────────┐
Explain My Solution ──────────┼──> Intent and Input Validation
Find/Generate Solution ──────┘
                                  ↓
                       Solution Retrieval/Generation
                                  ↓
                         Code Validation/Testing
                                  ↓
                         Execution Trace Capture
                                  ↓
                      Explanation + Scene Planning
                                  ↓
                         Video Cache Lookup
                                  ↓
                     Cache Hit? ──┬── Yes → Return Existing Video
                                  │
                                  └── No → Render New Video
                                                ↓
                                      Narration + Animation
                                                ↓
                                        FFmpeg Assembly
                                                ↓
                                         Cloudflare R2
                                                ↓
                                        Save Cache Metadata
                                                ↓
                                         Return to User
```
---
5. Authentication and Onboarding
5.1 Authentication methods
The application should support:
Email and password signup.
Email and password login.
Google OAuth login.
GitHub OAuth login.
Logout.
Password reset.
Email verification, depending on the chosen authentication
implementation.
Signup fields
Name.
Email.
Password.
Confirm password.
Confirm password is a frontend validation field; it does not need to be
stored in the database.
Login fields
The user may enter:
Email or username, depending on the selected identity design.
Password.
The user should also see Google and GitHub login options.
Authentication recommendation
For a student project, use a mature authentication implementation or
carefully implement OAuth through established libraries. Avoid building
OAuth protocol handling from scratch.
If using application-managed passwords:
Hash passwords using a suitable password-hashing algorithm.
Never store plaintext passwords.
Rate-limit login attempts.
Verify email if required.
Use secure session or token handling.
Keep secrets in backend environment variables or secret management.
OAuth should use authorization code flow with PKCE where applicable.
Validate provider responses and map provider identities to internal user
IDs.
5.2 Onboarding questions
Ask a short onboarding sequence after the first successful signup. Make
questions skippable where possible and allow users to update preferences
later.
Recommended four questions:
Question 1 --- What is your current DSA level?
Options:
Beginner --- learning fundamentals.
Intermediate --- solving common patterns.
Advanced --- preparing for challenging interview problems.
Purpose: choose the starting explanation depth and roadmap.
Question 2 --- Which programming language do you prefer?
Options:
Java
C++
Python
JavaScript
Other supported language
Purpose: default code language and solution retrieval preference.
Question 3 --- What is your main learning goal?
Options:
Build DSA fundamentals.
Prepare for coding interviews.
Practice LeetCode problems.
Revise and improve problem-solving.
Learn specific algorithms and data structures.
Purpose: roadmap and problem recommendations.
Do not overload onboarding with too many questions. Programming language
and explanation language should remain separate preferences.
Onboarding flow
``` text
Signup / OAuth
      ↓
Create or resolve user
      ↓
Check onboarding_completed
      ↓
Not completed?
   ├── Yes → Ask 4 preference questions
   │              ↓
   │        Save preferences
   │              ↓
   │        Create starter roadmap
   │              ↓
   └── No ─────────┘
                  ↓
            Open Pebble Chat
```
---
6. Frontend Design Direction
6.1 Design reference
The supplied screenshot is a visual reference for the desired
experience:
A centered, floating application window.
Soft pastel background.
Glass-like panels.
Rounded corners.
Subtle shadows and blur.
A compact left navigation rail.
A prominent central assistant area.
A small connection/action area near the top.
Suggestion chips above the chat input.
A rounded input with attachments, voice, and send controls.
Background application panels that create depth.
Pebble should borrow the layout language and glassmorphism
aesthetic, not the crypto-wallet content or branding.
6.2 Pebble visual identity
Suggested direction:
Light theme first, with a future dark theme.
Warm off-white background.
Soft blue, lavender, and pastel accent colors.
Frosted translucent cards.
Subtle borders and shadows.
Rounded panels, but not excessive pill-shaped elements.
Clear typography and generous whitespace.
A friendly pebble/companion icon.
Responsive layout for laptop, tablet, and mobile.
Avoid making every element translucent. Glassmorphism should be used
selectively for the main chat panel, floating input, modal, and selected
cards. Text and code panels should retain enough contrast for
readability.
6.3 Main workspace layout
``` text
┌────────────────────────────────────────────────────────────────┐
│ Pebble                                      Profile / Settings │
├─────────────┬──────────────────────────────────────────────────┤
│             │                                                  │
│ Navigation  │              Chat / Learning Workspace           │
│             │                                                  │
│ New Chat    │      Pebble: What are we learning today?         │
│ History     │                                                  │
│ Roadmap     │      [Suggested prompt] [Learn an algorithm]      │
│ Progress    │      [Explain my code] [Find a solution]          │
│ Saved       │                                                  │
│             │      Conversation messages                        │
│             │                                                  │
│             │      ┌──────────────────────────────────────┐      │
│             │      │ Ask about a problem...              │      │
│             │      │ Attach code | Language | Send       │      │
│             │      └──────────────────────────────────────┘      │
└─────────────┴──────────────────────────────────────────────────┘
```
6.4 Main pages
Landing page.
Signup.
Login.
Onboarding.
Chat workspace.
Problem learning workspace.
Video viewer.
Roadmap.
Progress dashboard.
Saved problems and history.
Profile and preferences.
6.5 Chat input controls
The chat input can support:
Text input.
Paste code.
Attach code or text files, with file type and size restrictions.
Learning mode selection.
Programming language selector.
Explanation language selector.
Generate video toggle/action.
Voice input, if implemented.
Send button.
Do not require every preference to be selected every time. Use
onboarding defaults and allow per-request overrides.
6.6 Suggested prompt chips
Show contextual chips such as:
Learn an algorithm.
Explain my code.
Find a LeetCode solution.
Generate a dry run.
Create an explanation video.
Continue my roadmap.
The chat should recognize intent but ask a clarification if the problem
or task is ambiguous.
---
7. Step-by-Step React Frontend Plan
Step 1 --- Create the frontend project
Use React, TypeScript, and Vite.
``` powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```
Step 2 --- Install frontend dependencies
``` powershell
npm install react-router-dom axios lucide-react
npm install -D tailwindcss
```
Configure Tailwind using the current installation instructions for the
selected version. Add a code editor such as Monaco when the learning
workspace is ready:
``` powershell
npm install @monaco-editor/react
```
Step 3 --- Establish design tokens
Define reusable CSS variables for:
Background.
Glass panel.
Border.
Text.
Muted text.
Accent.
Radius.
Shadow.
Blur.
Use these tokens across the app instead of hardcoding colors in every
component.
Step 4 --- Build authentication screens
Create:
Signup form.
Login form.
OAuth buttons.
Password visibility control.
Validation and error messages.
Loading states.
Terms/privacy links.
Frontend validation should improve UX, but backend validation remains
authoritative.
Step 5 --- Build onboarding
Create a short stepper or conversational questionnaire.
Store answers in frontend state while completing onboarding, then send
them to the backend. Show progress and allow back navigation.
Step 6 --- Build the chat shell
Create:
Navigation rail.
Chat history.
Conversation area.
Suggestion chips.
Chat composer.
Profile menu.
Use mock responses initially. Do not connect AI before the layout and
interaction flow are stable.
Step 7 --- Build the learning workspace
Create reusable panels for:
Problem statement.
Explanation.
Code.
Dry run.
Complexity.
Video player.
Use tabs or resizable panels. On mobile, use stacked sections or tabs.
Step 8 --- Add API integration
Create a centralized API client and typed request/response interfaces.
Frontend should call FastAPI endpoints; it should never connect directly
to NeonDB or expose Azure/R2 credentials.
Step 9 --- Add asynchronous job states
Video generation may take time. The UI should display:
Queued.
Preparing solution.
Validating code.
Generating explanation.
Rendering animation.
Generating narration.
Assembling video.
Completed.
Failed.
Provide retry or cancellation only when backend job semantics support
it.
Step 10 --- Polish and test
Test:
Responsive layout.
Keyboard navigation.
Form validation.
Loading states.
API errors.
Empty states.
OAuth return flow.
Chat history.
Video playback.
Accessibility and contrast.
---
8. Solution Repository and RAG
Source repository
Initial reference repository:
`https://github.com/Piyushshriv/Leetcode-Questions-Solutions`
The project proposes using this repository as a source for problem
summaries and solutions, with retrieval based on problem identity and
programming language.
Important distinction
This repository is a retrieval source, not automatically a complete
or authoritative LeetCode database.
Before ingesting it:
Review its license and terms.
Verify the repository structure and contents.
Record source URLs and attribution.
Confirm that content may be used and stored for the intended
purpose.
Avoid assuming every problem or language is present.
Avoid blindly copying content from other repositories into a public
product.
RAG design
For code solutions, exact metadata filtering should come before semantic
similarity.
Recommended retrieval sequence:
Parse the user's problem ID, URL, title, or statement.
Resolve a canonical problem identity.
Filter repository records by problem ID/slug.
Filter by requested programming language.
Retrieve the matching README/solution.
Retrieve relevant explanation chunks if needed.
Verify the retrieved solution's provenance.
Validate code before presenting it as verified.
Embeddings can help retrieve summaries, explanations, and concept-level
documents. They should not be the sole mechanism for finding a numbered
problem or selecting a language-specific code file.
Suggested ingestion pipeline
``` text
Approved GitHub repository
          ↓
Clone or fetch permitted content
          ↓
Inspect repository structure
          ↓
Extract problem ID, title, language, code, README
          ↓
Normalize metadata and source references
          ↓
Review license / attribution
          ↓
Store searchable metadata
          ↓
Chunk explanatory text for RAG
          ↓
Create embeddings for text chunks, if useful
          ↓
Retrieve by exact filters + semantic search
```
Retrieval record
Each ingested solution should track:
Source repository.
Source file path.
Source URL.
Problem ID and slug.
Programming language.
Content hash.
Ingestion timestamp.
License/attribution metadata.
Validation status.
Last checked timestamp.
Retrieval outcomes
Suitable solution found:
Retrieve the solution.
Check language and problem match.
Validate code.
Explain and visualize.
No suitable language solution:
Generate a solution in the requested language.
Validate it.
Store the generated artifact with provenance and validation status.
Problem identity or statement unavailable:
Ask the user for a problem URL, ID, or statement.
Do not fabricate problem constraints or official wording.
---
9. Solution Generation and Validation
9.1 Retrieval-first strategy
``` text
Problem + requested language
          ↓
Resolve problem identity
          ↓
Search exact solution metadata
          ↓
Suitable solution found?
   ├── Yes → Retrieve source and code
   └── No  → Generate solution using LLM
          ↓
Normalize code and entry point
          ↓
Compile / syntax check
          ↓
Run examples and tests in sandbox
          ↓
Pass?
   ├── Yes → Mark tests passed for tested cases
   └── No  → Repair attempt (limited retries)
                    ↓
              Re-test
                    ↓
          Return failure or partial result
          if validation remains unsuccessful
```
9.2 Validation requirements
A retrieved or generated solution should be checked for:
Correct problem identity.
Correct programming language.
Syntax or compilation.
Required entry point.
Example test cases.
Edge cases derived from constraints.
Time and memory limits where possible.
Output format.
Passing a small set of tests does not prove correctness. Use labels such
as:
Not tested.
Syntax checked.
Examples passed.
Additional tests passed.
Validation incomplete.
Failed.
9.3 Repair loop
Use a bounded repair loop, for example a small configurable number of
attempts.
The repair prompt should include:
Original problem statement.
Original code.
Compiler/runtime error.
Failed test input.
Expected output, if known.
Actual output.
Requested language.
Do not allow unbounded retries. If repair fails, show the issue and
offer the code for review rather than falsely marking it correct.
---
10. Execution Trace Engine
The execution trace is the source of truth for visualization.
Trace data may contain
Step number.
Event type.
Current line or source location.
Variable values.
Array/list state.
Pointer/index positions.
Stack/queue contents.
Map/set changes.
Recursive call and return.
Comparison result.
Mutation or swap.
Output state.
Example conceptual trace
``` json
{
  "step": 1,
  "event": "initialize",
  "variables": {
    "left": 0,
    "right": 4
  },
  "array": [1, 3, 5, 7, 9]
}
```
This is a conceptual example; the actual trace schema should be typed
and versioned.
Execution mechanisms
Different languages require different tracing strategies:
Python: controlled instrumentation or AST-based tracing.
Java: instrumented runner, debugger/agent, or carefully designed
execution harness.
C++: compiler instrumentation or a restricted tracing approach.
JavaScript: instrumented execution environment.
A simple text parser of source code is not enough for reliable execution
traces.
Safety
Run user and generated code in a sandbox, not inside the FastAPI
process.
The sandbox should enforce:
CPU timeout.
Memory limit.
Restricted filesystem.
No network access by default.
Process isolation.
Output size limit.
Cleanup after execution.
---
11. AI Explanation Generator
The explanation generator should accept:
Problem statement or concept.
Validated solution.
Programming language.
Explanation language.
Execution trace, when available.
Output sections
Problem summary.
Inputs and outputs.
Constraints.
Intuition.
Brute-force approach.
Optimized approach.
Code.
Step-by-step explanation.
Dry-run narration.
Time complexity.
Space complexity.
Edge cases.
Common mistakes.
Explanation languages
Initial supported explanation/narration languages:
English.
Hindi.
Programming language and explanation language are independent.
For example:
Java code + Hindi explanation.
Python code + English explanation.
Explanation styles
Beginner-friendly.
Technical.
Both.
Grounding
The model should be provided with the actual problem statement and
selected solution. If a statement is unavailable, the system should ask
for it or retrieve it through an authorized source.
The model must not invent constraints, sample outputs, or claim that a
solution is official without evidence.
---
12. Video Generation Pipeline
Components
LLM: explanation, scene plan, narration, code generation/repair.
Execution trace engine: actual program state.
Manim: animation.
Azure AI Speech: narration audio.
FFmpeg: audio/video assembly and encoding.
Cloudflare R2: final video storage.
FastAPI: orchestration and job API.
Pipeline
``` text
User request
    ↓
Intent and preference resolution
    ↓
Problem / concept resolution
    ↓
Solution retrieval or generation
    ↓
Code validation
    ↓
Execution trace capture
    ↓
Explanation generation
    ↓
Structured scene plan
    ↓
Schema and trace validation
    ↓
Video cache fingerprint
    ↓
Cache lookup
    ├── Hit → Return existing video
    └── Miss
          ↓
      Manim animation
          +
      Azure Speech narration
          ↓
      FFmpeg synchronization
          ↓
      Output validation
          ↓
      Upload to Cloudflare R2
          ↓
      Store video metadata in NeonDB
          ↓
      Return video reference
```
Scene types
Use a controlled set of reusable scenes:
Intro.
Problem statement.
Example input/output.
Algorithm overview.
Array or pointer visualization.
Stack/queue visualization.
Tree/graph visualization.
Code highlight.
Dry-run step.
Complexity summary.
Outro.
The LLM should produce a scene plan conforming to the schema. Manim
should render from approved scene types and trace data, rather than
executing arbitrary model-generated Python.
Narration
Narration should be created from the validated explanation and scene
plan.
Generate narration per scene or segment.
Use Azure Speech.
Capture actual audio duration or timing metadata.
Synchronize scene transitions to narration.
Avoid estimating timing only from word count.
FFmpeg
FFmpeg can:
Combine scene clips.
Add narration.
Synchronize audio and video.
Normalize audio levels.
Encode the final MP4.
Verify output duration and format.
---
13. Cloudflare R2 Video Storage and Cache
Why R2
Cloudflare R2 is intended for object storage of large generated media.
NeonDB should store metadata and references, not the MP4 binary itself.
Storage flow
Video worker renders a video.
Worker validates the output.
Worker uploads the MP4 to R2.
Worker records the object key and metadata in NeonDB.
Backend returns a playback URL or signed URL.
Frontend plays the video.
Cache requirement
If an equivalent video already exists, Pebble should return it instead
of regenerating it.
Cache key
Create a deterministic fingerprint from the relevant inputs:
``` text
problem_or_concept_id
+ problem_statement_hash
+ solution_hash
+ programming_language
+ explanation_language
+ explanation_style
+ scene_template_version
+ narration_voice/configuration
+ video_render_version
```
Hash the normalized fingerprint to produce a cache key.
Cache lookup
``` text
Request video
     ↓
Build fingerprint
     ↓
Search completed video record in NeonDB
     ↓
Matching record exists?
   ├── Yes → Check object availability
   │            ├── Available → Return video reference
   │            └── Missing → Mark cache stale and regenerate
   └── No → Create video job
                  ↓
             Render video
                  ↓
             Upload to R2
                  ↓
             Save cache record
                  ↓
             Return video
```
Cache correctness
Do not cache only by LeetCode problem number.
The same problem may have:
Different programming languages.
Different solutions.
Different explanation languages.
Different explanation styles.
Different narration voices.
Different scene templates.
A video should be reused only when the requested learning artifact is
compatible with the cached artifact.
R2 security
Keep R2 access keys on the backend.
Use private buckets by default.
Return signed URLs or controlled playback access.
Apply expiration to signed URLs.
Never expose account-level R2 secrets to React.
Consider retention and deletion policies.
Track object key, content hash, size, duration, and creation time.
---
14. NeonDB Data Model
NeonDB is the primary relational database for application metadata and
user progress.
14.1 `users`
`id`
`name`
`email`
`created_at`
`onboarding_completed`
14.2 `auth_identities`
For OAuth or external identity mapping:
`id`
`user_id`
`provider`
`provider_subject`
`created_at`
Use a unique constraint on provider + provider subject.
14.3 `user_preferences`
`user_id`
`experience_level`
`preferred_language`
`explanation_language`
`explanation_style`
`learning_goal`
`updated_at`
14.4 `problems`
`id`
`source`
`external_problem_id`
`title`
`slug`
`difficulty`
`topics`
`canonical_url`
`statement_hash`
`created_at`
Store full problem statements only when permitted.
14.5 `solutions`
`id`
`problem_id`
`language`
`code`
`source_type`
`source_url`
`content_hash`
`validation_status`
`created_at`
14.6 `solution_tests`
`id`
`solution_id`
`test_type`
`status`
`test_summary`
`created_at`
Do not store sensitive test data or unbounded execution output.
14.7 `execution_traces`
`id`
`solution_id`
`trace_version`
`trace_storage_key` or structured trace reference
`status`
`created_at`
Large traces may be stored in object storage; keep queryable metadata in
NeonDB.
14.8 `conversations`
`id`
`user_id`
`title`
`created_at`
`updated_at`
14.9 `messages`
`id`
`conversation_id`
`role`
`content`
`mode`
`created_at`
Consider storing structured message metadata separately. Apply retention
controls and avoid storing unnecessary sensitive content.
14.10 `user_progress`
`id`
`user_id`
`problem_id`
`status`
`attempt_count`
`last_attempted_at`
`solved_at`
Use a unique constraint on user + problem if each user should have one
progress row per problem.
14.11 `roadmaps`
`id`
`user_id`
`title`
`goal`
`created_at`
14.12 `roadmap_problems`
`id`
`roadmap_id`
`problem_id`
`sequence_number`
`status`
14.13 `video_jobs`
`id`
`user_id`
`problem_id` or concept reference
`solution_id`
`fingerprint`
`status`
`stage`
`error_code`
`created_at`
`completed_at`
14.14 `generated_videos`
`id`
`video_job_id`
`fingerprint`
`r2_object_key`
`content_type`
`size_bytes`
`duration_seconds`
`render_version`
`created_at`
Use a unique fingerprint constraint for completed reusable artifacts
where appropriate. Handle concurrent requests so two users requesting
the same video do not unnecessarily launch duplicate renders.
---
15. Backend Architecture
Recommended backend modules
Authentication and user management.
User preferences and onboarding.
Chat and intent resolution.
Problem catalog and source retrieval.
RAG retrieval.
Solution generation.
Code validation.
Execution tracing.
Explanation generation.
Scene planning.
Video cache service.
Video job orchestration.
Manim rendering worker.
Azure Speech service.
R2 storage service.
Progress and roadmap service.
Suggested API endpoints
Authentication and profile
Method   Endpoint                  Purpose
---
POST     `/auth/register`          Create account
POST     `/auth/login`             Login
POST     `/auth/logout`            Logout
GET      `/users/me`               Get current profile
PATCH    `/users/me`               Update profile
GET      `/users/me/preferences`   Get preferences
PUT      `/users/me/preferences`   Save preferences
POST     `/users/me/onboarding`    Complete onboarding
OAuth callback routes depend on the authentication implementation.
Chat and learning
Method   Endpoint                         Purpose
---
POST     `/conversations`                 Create conversation
GET      `/conversations`                 List user's conversations
GET      `/conversations/{id}`            Load conversation
POST     `/conversations/{id}/messages`   Send message
POST     `/learning/resolve`              Resolve mode, problem, and preferences
POST     `/learning/explanation`          Generate explanation
POST     `/learning/dry-run`              Generate or retrieve trace
Problem and solution
Method   Endpoint                     Purpose
---
GET      `/problems`                  Search problem metadata
GET      `/problems/{id}`             Get problem details
GET      `/problems/{id}/solutions`   List available solutions
POST     `/solutions/generate`        Generate solution
POST     `/solutions/{id}/validate`   Validate solution
Video
Method   Endpoint                    Purpose
---
POST     `/video-jobs`               Request video
GET      `/video-jobs/{id}`          Get status
GET      `/video-jobs/{id}/result`   Get playback reference
POST     `/video-jobs/{id}/retry`    Retry eligible failed job
The backend should return a job ID for long-running work instead of
keeping the HTTP request open until the video is rendered.
---
16. Project Folder Structure
A monorepo is recommended for the initial project so frontend, backend,
and video worker can evolve together.
``` text
pebble/
│
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── project-overview.md
│   ├── architecture.md
│   ├── api-spec.md
│   ├── database-design.md
│   ├── security.md
│   └── video-pipeline.md
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes/
│       │   ├── LandingPage.tsx
│       │   ├── LoginPage.tsx
│       │   ├── SignupPage.tsx
│       │   ├── OnboardingPage.tsx
│       │   ├── ChatPage.tsx
│       │   ├── LearningPage.tsx
│       │   ├── RoadmapPage.tsx
│       │   └── ProfilePage.tsx
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   └── Topbar.tsx
│       │   ├── auth/
│       │   │   ├── LoginForm.tsx
│       │   │   ├── SignupForm.tsx
│       │   │   └── OAuthButtons.tsx
│       │   ├── onboarding/
│       │   │   ├── OnboardingStepper.tsx
│       │   │   └── PreferenceQuestion.tsx
│       │   ├── chat/
│       │   │   ├── ChatMessage.tsx
│       │   │   ├── ChatComposer.tsx
│       │   │   ├── PromptChips.tsx
│       │   │   └── ChatHistory.tsx
│       │   ├── learning/
│       │   │   ├── ProblemPanel.tsx
│       │   │   ├── ExplanationPanel.tsx
│       │   │   ├── CodePanel.tsx
│       │   │   ├── DryRunPanel.tsx
│       │   │   └── ComplexityPanel.tsx
│       │   └── video/
│       │       ├── VideoPlayer.tsx
│       │       └── VideoJobStatus.tsx
│       │
│       ├── services/
│       │   ├── api.ts
│       │   ├── auth.service.ts
│       │   ├── chat.service.ts
│       │   ├── problem.service.ts
│       │   └── video.service.ts
│       │
│       ├── hooks/
│       ├── types/
│       ├── utils/
│       └── styles/
│           ├── globals.css
│           └── tokens.css
│
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │
│   └── app/
│       ├── main.py
│       ├── config.py
│       │
│       ├── api/
│       │   ├── auth.py
│       │   ├── users.py
│       │   ├── onboarding.py
│       │   ├── conversations.py
│       │   ├── problems.py
│       │   ├── solutions.py
│       │   ├── learning.py
│       │   └── videos.py
│       │
│       ├── core/
│       │   ├── security.py
│       │   ├── dependencies.py
│       │   └── exceptions.py
│       │
│       ├── db/
│       │   ├── engine.py
│       │   ├── base.py
│       │   └── session.py
│       │
│       ├── models/
│       │   ├── user.py
│       │   ├── problem.py
│       │   ├── solution.py
│       │   ├── conversation.py
│       │   ├── progress.py
│       │   └── video.py
│       │
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── user.py
│       │   ├── problem.py
│       │   ├── solution.py
│       │   ├── explanation.py
│       │   └── video.py
│       │
│       ├── repositories/
│       │   ├── user_repository.py
│       │   ├── problem_repository.py
│       │   ├── solution_repository.py
│       │   └── video_repository.py
│       │
│       ├── services/
│       │   ├── auth_service.py
│       │   ├── onboarding_service.py
│       │   ├── chat_service.py
│       │   ├── problem_service.py
│       │   ├── solution_service.py
│       │   ├── explanation_service.py
│       │   ├── trace_service.py
│       │   ├── video_service.py
│       │   └── cache_service.py
│       │
│       ├── integrations/
│       │   ├── github/
│       │   │   ├── client.py
│       │   │   └── repository_ingestion.py
│       │   ├── azure/
│       │   │   ├── llm_client.py
│       │   │   └── speech_client.py
│       │   └── r2/
│       │       └── storage_client.py
│       │
│       ├── rag/
│       │   ├── ingestion.py
│       │   ├── chunking.py
│       │   ├── embeddings.py
│       │   ├── retrieval.py
│       │   └── metadata.py
│       │
│       ├── code_execution/
│       │   ├── sandbox.py
│       │   ├── test_runner.py
│       │   ├── language_adapters/
│       │   └── trace_capture/
│       │
│       └── workers/
│           ├── video_worker.py
│           └── job_runner.py
│
├── video-engine/
│   ├── requirements.txt
│   ├── render.py
│   ├── scenes/
│   │   ├── intro.py
│   │   ├── problem_scene.py
│   │   ├── array_scene.py
│   │   ├── code_scene.py
│   │   ├── dry_run_scene.py
│   │   └── complexity_scene.py
│   ├── templates/
│   └── utils/
│
├── scripts/
│   ├── ingest_solutions.py
│   ├── seed_problem_metadata.py
│   └── verify_storage.py
│
└── tests/
    ├── frontend/
    ├── backend/
    ├── code_execution/
    └── video/
```
Folder structure principles
`frontend/components`: reusable UI only.
`frontend/services`: API communication.
`backend/api`: HTTP routes and request/response handling.
`backend/services`: business logic.
`backend/repositories`: database queries.
`backend/integrations`: external provider clients.
`backend/rag`: ingestion and retrieval.
`backend/code_execution`: isolated execution and trace capture.
`backend/workers`: long-running jobs.
`video-engine`: Manim scenes and rendering.
`scripts`: ingestion and maintenance.
`tests`: automated validation.
Do not put all business logic inside FastAPI route functions.
---
17. Technology Stack
---
Layer                   Technology              Role
---
Frontend                React                   UI and user interaction
Language                TypeScript              Type-safe frontend
Build                   Vite                    Development and build
Styling                 Tailwind CSS + CSS      Glassmorphism and
variables               responsive UI
Routing                 React Router            Page navigation
HTTP                    Axios or Fetch          API requests
Icons                   Lucide React            UI icons
Code editor             Monaco Editor           Code display/editing
Backend                 FastAPI                 API and orchestration
Backend language        Python                  AI, retrieval, execution
orchestration
Database                NeonDB PostgreSQL       Users, metadata,
progress, job records
ORM                     SQLAlchemy              Database models and
access
Migrations              Alembic                 Schema versioning
AI model                Azure AI deployment     Code/explanation/scene
generation
Speech                  Azure AI Speech         Narration
RAG                     Embeddings + retrieval  Explanatory corpus
layer                   retrieval
Animation               Manim                   Algorithm scenes
Media                   FFmpeg                  Audio/video assembly
Storage                 Cloudflare R2           Generated video and
media objects
Code testing            Isolated sandbox        Compilation, execution,
tests
Source control          Git + GitHub            Version control
Architecture choices
NeonDB stores relational metadata; R2 stores large media.
FastAPI owns credentials and external service calls.
React consumes API responses only.
Manim renders from validated structured scenes.
AI-generated code is not trusted until validated.
RAG uses exact metadata filters for problem/language and semantic
retrieval for explanatory text.
---
18. Security and DSA-Only Scope
Pebble must only create educational videos about DSA problems,
algorithms, data structures, coding solutions, and closely related
programming concepts.
It must not become a general-purpose video generator for arbitrary
real-world topics such as weather, classroom scenes, travel, or
unrelated entertainment.
18.1 Intent classification
Every request should pass through a backend intent gate.
Allowed intent examples:
Explain LeetCode problem 150.
Teach Binary Search.
Explain my Java solution.
Show a stack dry run.
Compare BFS and DFS.
Generate a DSA educational video.
Out-of-scope examples:
Generate a weather forecast video.
Make a classroom animation unrelated to programming.
Create a travel video.
Generate general entertainment or unrelated real-world videos.
18.2 Request pipeline
``` text
User request
    ↓
Normalize input
    ↓
Intent classification
    ↓
DSA-related?
   ├── Yes → Resolve problem/concept/code
   │              ↓
   │        Continue learning pipeline
   └── No  → Politely explain Pebble's scope
              and suggest a DSA-related request
```
18.3 Guardrails
Validate scope on the backend, not only in React.
Use a structured intent result.
Check that the request contains a supported problem, algorithm, data
structure, or code-learning goal.
Do not let the user prompt override the platform's scope.
Recheck the scene plan before rendering.
Allow only approved Manim scene types.
Do not execute arbitrary model-generated Python or scene code.
Limit file attachments to supported text/code formats and sizes.
Reject unsupported or suspicious inputs.
Keep a safe fallback response for ambiguous requests.
18.4 Security controls
OAuth provider verification.
Secure password hashing if password authentication is used.
Session/token expiration and revocation.
Rate limits for login, chat, code execution, and video jobs.
Per-user authorization for conversations and video jobs.
Backend-only database and cloud-storage secrets.
Sandbox limits for generated/user code.
R2 private access and signed URLs.
Request and output size limits.
Safe error responses.
Logging without secrets or unnecessary personal data.
---
19. Reliability and Quality
AI reliability
Use structured output schemas.
Ground solution generation in the problem statement.
Store source and generation provenance.
Separate generated from retrieved code.
Track validation status.
Do not claim correctness based only on a generated explanation.
Use a bounded repair loop.
Trace reliability
Trace from actual execution when possible.
Validate trace schema.
Ensure scene values match trace values.
Avoid LLM-invented state transitions.
Clearly indicate when a trace is illustrative rather than
execution-derived.
Video reliability
Run rendering as asynchronous work.
Track job stages.
Use unique job directories.
Retry transient failures with limits.
Verify final MP4.
Upload only completed output.
Confirm R2 object availability before marking the job complete.
Store the renderer/template version in cache metadata.
Cost management
Reuse matching videos.
Cache validated solutions and explanations when appropriate.
Set per-user quotas.
Limit video duration and render complexity.
Avoid duplicate concurrent jobs for the same fingerprint.
Track AI tokens, render duration, and storage usage.
---
20. MVP and Development Roadmap
Phase 1 --- Foundation
Create monorepo.
Build React + Vite frontend.
Build FastAPI backend.
Configure NeonDB.
Add environment configuration.
Add API health check.
Establish frontend/backend connection.
Outcome: Running app with database connectivity.
Phase 2 --- Authentication and onboarding
Signup/login.
Google OAuth.
GitHub OAuth.
Profile and preferences.
Four onboarding questions.
Save onboarding state.
Outcome: User-specific learning preferences.
Phase 3 --- Chat workspace
Glassmorphism layout.
Chat history.
Prompt chips.
Chat composer.
Learning mode selector.
Language and explanation preferences.
Backend intent classification.
Outcome: User can submit a supported DSA request.
Phase 4 --- Problem catalog and GitHub retrieval
Review source repository license.
Ingest permitted problem metadata and solutions.
Normalize problem IDs and languages.
Build exact metadata retrieval.
Add RAG for explanatory text.
Show source references.
Outcome: Retrieve supported existing solutions.
Phase 5 --- Solution generation and validation
Add LLM integration.
Generate code when retrieval misses.
Add compile/syntax checks.
Add test runner.
Add bounded repair attempts.
Store validation metadata.
Outcome: Retrieved/generated solutions have transparent test status.
Phase 6 --- Explanation and trace
Explanation schema.
Beginner/technical styles.
English/Hindi support.
Execution trace capture.
Basic array and pointer visualization.
Outcome: Students can understand and inspect a solution.
Phase 7 --- Video generation
Scene schema.
Manim scene templates.
Azure Speech integration.
FFmpeg assembly.
R2 upload.
NeonDB video metadata.
Job status API.
Outcome: End-to-end educational video generation.
Phase 8 --- Video cache
Deterministic fingerprint.
Cache lookup.
R2 object verification.
Duplicate-job prevention.
Cache invalidation/versioning.
Outcome: Reuse equivalent videos instead of regenerating.
Phase 9 --- Roadmap and progress
Problem completion tracking.
Bookmarks.
Roadmap templates.
Dashboard.
Topic progress.
Recommendation logic.
Outcome: Personalized DSA learning experience.
Phase 10 --- Testing and deployment
Frontend tests.
Backend unit and integration tests.
Auth/security testing.
Sandbox testing.
Video pipeline tests.
Load and cost checks.
Deployment and monitoring.
---
21. MVP Definition
Do not attempt every feature at once.
First MVP
Signup/login.
Onboarding preferences.
Chat workspace.
Problem ID input.
Retrieval from a small permitted solution dataset.
One initial programming language, preferably Java.
Explanation generation.
Basic code validation.
Simple execution trace.
Basic visualization.
Store user and problem data in NeonDB.
Second milestone
Add Python/C++.
Add Hindi explanations.
Add user-submitted code.
Add richer trace visualization.
Add Manim scenes.
Add Azure Speech and FFmpeg.
Third milestone
Add Cloudflare R2.
Add video cache.
Add asynchronous video jobs.
Add roadmap and progress.
Add more languages and scene templates.
MVP success criteria
A student can sign in, configure preferences, ask for a supported DSA
problem, retrieve or generate a solution, receive an explanation,
inspect a trace, and save progress.
Video generation is the central advanced feature, but the underlying
retrieval, validation, and trace pipeline should be stable before making
it the only learning path.
---
22. Final System Pipeline
``` text
                  ┌──────────────────────┐
                  │ Signup / Login      │
                  │ Google / GitHub     │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ Onboarding           │
                  │ Level / Goal / Lang │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ Pebble Chat          │
                  │ Ask what to learn    │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ DSA Scope Gate       │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ Learning Mode        │
                  │ Algorithm / Code /   │
                  │ Problem solution     │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ Problem Resolution   │
                  │ ID / URL / Statement│
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ GitHub RAG / Search  │
                  │ Exact ID + Language  │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ Solution Found?      │
                  └───────┬───────┬──────┘
                          │       │
                         Yes      No
                          │       ↓
                          │  ┌──────────────────┐
                          │  │ LLM Code         │
                          │  │ Generation       │
                          │  └────────┬─────────┘
                          └────────────┘
                                       ↓
                            ┌────────────────────┐
                            │ Sandbox Validation │
                            │ Compile + Tests    │
                            └─────────┬──────────┘
                                      ↓
                            ┌────────────────────┐
                            │ Execution Trace    │
                            │ Actual code states │
                            └─────────┬──────────┘
                                      ↓
                            ┌────────────────────┐
                            │ Explanation +      │
                            │ Scene Planning      │
                            └─────────┬──────────┘
                                      ↓
                            ┌────────────────────┐
                            │ Video Fingerprint  │
                            │ Cache Lookup       │
                            └─────────┬──────────┘
                                      ↓
                            ┌────────────────────┐
                            │ Cache Hit?         │
                            └──────┬───────┬─────┘
                                   │       │
                                  Yes      No
                                   │       ↓
                                   │  ┌──────────────────┐
                                   │  │ Manim Animation  │
                                   │  └────────┬─────────┘
                                   │           ↓
                                   │  ┌──────────────────┐
                                   │  │ Azure Speech     │
                                   │  └────────┬─────────┘
                                   │           ↓
                                   │  ┌──────────────────┐
                                   │  │ FFmpeg Assembly  │
                                   │  └────────┬─────────┘
                                   │           ↓
                                   │  ┌──────────────────┐
                                   │  │ Upload to R2     │
                                   │  └────────┬─────────┘
                                   │           ↓
                                   │  ┌──────────────────┐
                                   │  │ Save metadata    │
                                   │  │ in NeonDB        │
                                   │  └────────┬─────────┘
                                   └────────────┴─────────┐
                                                        ↓
                                             ┌──────────────────┐
                                             │ Return video and │
                                             │ learning content │
                                             └──────────────────┘
```
---
23. Project Summary
Pebble is a personalized AI-based DSA learning and educational video
platform.
User-facing experience
Secure signup/login with Google and GitHub options.
Four-question onboarding.
Friendly chatbot interface.
Problem, algorithm, and user-code learning modes.
Programming-language and explanation-language selection.
Code explanations and dry runs.
Animated educational videos.
Progress and roadmap.
Backend experience
FastAPI API layer.
GitHub solution retrieval and RAG.
LLM-based code generation and explanation.
Sandboxed validation.
Execution trace capture.
Manim animation.
Azure Speech narration.
FFmpeg assembly.
Cloudflare R2 storage.
NeonDB metadata and progress.
Deterministic video cache.
Core principle
> **Retrieve when possible. Generate when needed. Validate before
> teaching. Visualize actual execution. Reuse matching videos.**
This is the foundation for building Pebble as a reliable, secure, and
extensible DSA learning platform.