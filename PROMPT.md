MICRO DRAMA SaaS — INDEPENDENT MVP BUILD CHALLENGE

ROLE

You are an autonomous senior software architect, full-stack developer, AI workflow engineer, and DevOps engineer.

Your mission is to independently design, build, test, and deliver a working MVP of a commercial Micro Drama SaaS platform.

Do not merely create a plan or prototype screenshots. Build a functional application.

1. AUTONOMOUS SKILL PREPARATION

Before development:

1. Audit your available tools, skills, plugins, and development environment.
2. Identify the skills required for this project.
3. Search for suitable existing skills, including GitHub repositories and official documentation.
4. Install and configure the necessary skills yourself.
5. Verify that installed skills and dependencies actually work.
6. Create additional project-specific skills if necessary.
7. Document installed skills and their sources.

Required competency areas:

- Full-stack development
- SaaS architecture
- Multi-tenant architecture
- Frontend UI/UX
- Backend engineering
- PostgreSQL and database design
- Authentication and OAuth
- API development
- AI/LLM integration
- Prompt engineering
- Story and script generation
- Playwright browser automation
- Browser session management
- Video processing and FFmpeg
- Testing and debugging
- Docker and DevOps
- Git and GitHub workflow
- Security engineering

Do not install unnecessary tools or duplicate capabilities.

2. PRODUCT OBJECTIVE

Build an AI-powered Micro Drama Production SaaS.

The platform enables users to create short drama series from initial story concepts through scripts, characters, scenes, prompts, and final video production.

Target platform:

- Web SaaS first.
- Android-compatible responsive interface.
- Architecture ready for future Android application development.

3. CORE MODULES

A. User Management

- Registration
- Login
- User dashboard
- User profile
- Project ownership
- Multi-tenant data isolation

B. Project Studio

- Create multiple drama projects.
- Project descriptions.
- Genre and themes.
- Project settings.
- Production status.

C. Series Bible

- Story premise.
- Main plot.
- Subplots.
- Character relationships.
- World settings.
- Tone and visual style.
- Ending direction.
- Episode structure.

D. Character Studio

- Character profiles.
- Physical appearance.
- Personality.
- Background.
- Costume.
- Character reference images.
- Character consistency instructions.

Support at least six characters per project.

E. Location Studio

- Location profiles.
- Environment descriptions.
- Visual references.
- Lighting and atmosphere.
- Location consistency instructions.

F. Story Engine

- Story idea generation.
- Story development.
- Episode outline.
- 20-episode series generation.
- Conflict development.
- Cliffhangers.
- Character development.

G. Scene Engine

- Episode breakdown.
- Scene breakdown.
- Shot lists.
- Camera directions.
- Character actions.
- Dialogues.
- Scene continuity.

H. Prompt Studio

Generate structured prompts for:

- Character images.
- Location images.
- Scene images.
- Video generation.
- Camera movements.
- Character actions.
- Dialogue and audio.

Provide editable prompts and copy/export functionality.

I. Episode Manager

- Episode list.
- Production status.
- Scene status.
- Production progress.
- Revision history.
- Production costs.
- Generated assets.
- Export management.

J. Google Account Manager

Design a multi-account management system.

Requirements:

- Each SaaS user connects their own Google accounts.
- Maximum 20 connected accounts per SaaS user.
- Strict isolation between users.
- Independent browser sessions and storage.
- Session status monitoring.
- Account selection per project.
- Connect and disconnect accounts.
- Encrypted session storage.

Never store Google passwords directly.

Do not use account switching to circumvent Google quotas or restrictions.

K. Flow Bridge

Integrate a workflow for Google Flow.

Initial MVP:

- Prepare image and video prompts.
- Prepare reference assets.
- Organize production tasks.
- Export prompts and references.
- Track manually generated results.
- Import generated video files into the project.

Design an extensible automation interface for future browser automation.

Do not assume Google Flow provides a public API.

Do not implement unauthorized automation or bypass CAPTCHA, access controls, rate limits, or platform restrictions.

L. Post Production

Use FFmpeg where appropriate.

Provide:

- Video assembly.
- Audio integration.
- Subtitle integration.
- Basic rendering.
- Final episode export.

4. TECHNICAL ARCHITECTURE

Choose a maintainable technology stack.

Suggested options:

Frontend:

- Next.js
- React
- TypeScript
- Tailwind CSS

Backend:

- Python FastAPI or another justified backend.

Database:

- PostgreSQL.

Infrastructure:

- Docker
- Redis or equivalent queue system if necessary.
- Local or S3-compatible object storage.
- Linux VPS deployment.

Browser automation:

- Playwright.
- Browser Use where appropriate.

You may choose alternatives when technically justified.

Explain your decisions.

5. MULTI-TENANT SECURITY

This is a critical requirement.

Implement:

- Strict tenant isolation.
- User-level authorization.
- Project ownership validation.
- Database access controls.
- Secure authentication.
- Secure session handling.
- Protected file access.
- Audit logs for sensitive operations.

One user must never be able to access another user's projects, files, accounts, sessions, or production history.

6. MVP DEVELOPMENT RULES

Build a working MVP, not an oversized enterprise platform.

Prioritize:

1. Working authentication.
2. Functional dashboard.
3. Project management.
4. Series Bible.
5. Character and Location Studio.
6. Story and Scene Engine.
7. Prompt Studio.
8. Episode Manager.
9. Flow Bridge.
10. Multi-account architecture.

Avoid unnecessary complexity.

Use modular architecture so additional capabilities can be added later.

Do not leave critical functionality as fake buttons or static mockups.

7. INDEPENDENT DEVELOPMENT

You are participating in a three-agent independent build challenge.

Do not assume another agent will implement missing functionality.

Do not copy another agent's implementation.

Build your own complete implementation using your available environment and tools.

Create a separate Git branch or repository for your implementation.

8. TESTING REQUIREMENTS

Test the actual application.

At minimum:

- Registration and login.
- Create and edit projects.
- Create Series Bible.
- Create six characters.
- Create locations.
- Generate a 20-episode outline.
- Generate scene breakdowns.
- Generate structured prompts.
- Save and retrieve production progress.
- Upload and retrieve assets.
- Test two independent user accounts.
- Verify tenant isolation.
- Verify account limit enforcement at 20 accounts.
- Test export functionality.

Report tests that fail honestly.

Do not claim a feature works without testing it.

9. DELIVERABLES

Deliver:

1. Complete source code.
2. Working application.
3. Database schema and migrations.
4. Docker configuration.
5. Environment configuration example.
6. Installation instructions.
7. Deployment instructions.
8. API documentation.
9. Skill installation report.
10. Architecture documentation.
11. Testing report.
12. Known limitations.
13. Future development recommendations.

10. EXECUTION INSTRUCTIONS

Work autonomously.

Do not stop after producing a proposal.

Do not ask unnecessary questions.

Make reasonable technical decisions and document them.

If a dependency, service, or feature is unavailable, implement the best functional alternative and clearly document the limitation.

Start with environment and skill audits, then architecture, implementation, testing, and delivery.

Your final report must clearly state:

- What you built.
- What works.
- What was tested.
- What remains incomplete.
- How to run the application.
- Where the source code is located.
- What should be improved next.

MISSION: DELIVER A WORKING MICRO DRAMA SaaS MVP.
