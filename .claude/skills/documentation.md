# Documentation Skill

Guidance for creating and maintaining MyGym documentation for GitHub Pages. **All documentation must be created as HTML** for optimal presentation and styling on GitHub Pages.

## Overview

MyGym documentation structure:

- **Main User Page** (`docs/index.html`) — Primary entry point with MyGym overview and feature links (user-focused, purple gradient theme)
- **User Feature Guides** (`docs/user/*.html`) — Detailed how-to guides for each feature (purple gradient theme)
- **Technical Documentation** (`docs/technical/*.html`) — Architecture, implementation, and developer guides (blue gradient theme, secondary/discrete links in footer)
- **Shared Resources** (`docs/*.md`) — Database migrations, setup guides (markdown acceptable for longer reference docs)

All documentation is published via GitHub Pages as HTML files. The main page is user-focused with app overview and feature links; technical and reference docs are accessible via discrete footer links.

## User Documentation

**Purpose**: Teach end users how to use MyGym features  
**Location**: `docs/user/`  
**Audience**: People using the application  
**Format**: HTML (rendered on GitHub Pages)

### Structure

Each user feature should have its own HTML file:

```
docs/user/
├── index.html (Hub with links to all user docs)
├── LOGIN_SIGNUP.html (Feature: Authentication)
├── PROFILE_SETUP.html (Feature: User profile)
├── PROGRAM_GENERATION.html (Feature: Workout programs)
├── WORKOUT_TRACKING.html (Feature: Daily tracking)
├── PROGRESS_ANALYTICS.html (Feature: Analytics)
└── ACCOUNT_MANAGEMENT.html (Feature: Account settings)
```

### Writing User Documentation

**Format**: HTML with embedded CSS styling  
**Tone**: Friendly, clear, non-technical, conversational

**HTML Structure for each feature**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>[Feature Name] - MyGym</title>
    <style>
        /* Consistent styling — see LOGIN_SIGNUP.html for reference */
    </style>
</head>
<body>
    <header>
        <h1>🎯 [Feature Name]</h1>
        <p>Brief description of feature</p>
    </header>

    <div class="content">
        <h2>Overview</h2>
        <!-- 1-2 sentences describing feature -->

        <h2>Before You Start</h2>
        <!-- Prerequisites and setup -->

        <h2>How to [Main Action]</h2>
        <div class="step">
            <ol>
                <li>Step one...</li>
                <li>Step two...</li>
            </ol>
        </div>

        <h2>Troubleshooting</h2>
        <div class="faq-item">
            <strong>❓ Common issue</strong>
            <p>Solution here</p>
        </div>

        <h2>Tips & Tricks</h2>
        <!-- Best practices -->

        <h2>Related Features</h2>
        <!-- Links to related docs -->
    </div>
</body>
</html>
```

**Styling Guidelines**:
- Use color scheme: `#667eea` (primary), `#764ba2` (secondary)
- Include emoji in headers for visual appeal
- Use callout boxes for tips (green), warnings (orange), notes (blue)
- Responsive design with `max-width: 900px`
- Reference existing `LOGIN_SIGNUP.html` for style template

**Content Guidelines**:

- Write in second person ("You can...", "Your profile")
- Avoid jargon; if technical terms needed, explain them
- Use consistent terminology throughout
- Include examples when helpful
- Focus on the user's goal, not technical implementation
- Break complex tasks into small steps
- Provide "why" when it helps understanding

**Examples**:

❌ Bad: "JWT tokens are stored in HTTP-only cookies to prevent XSS attacks"  
✅ Good: "Your login is secure — we protect your session automatically"

❌ Bad: "Invoke POST /api/v1/programs to generate a workout"  
✅ Good: "Click 'Generate Program' and we'll create your workout based on your goals"

### Updating User Docs Index

When creating a new user feature doc, update `docs/user/index.html`:

```html
<h2>Feature Category</h2>
<ul>
    <li><a href="NEW_FEATURE.html">Feature Name</a> - Brief description</li>
</ul>
```

And update the quick-links section:

```html
<div class="doc-sections">
    <a href="NEW_FEATURE.html">🎯 Feature Name</a>
</div>
```

---

## Technical Documentation

**Purpose**: Explain implementation details, architecture, APIs, and patterns  
**Location**: `docs/technical/`  
**Audience**: Developers, DevOps engineers, code reviewers  
**Format**: HTML (rendered on GitHub Pages)

### Structure

Organize by system/component:

```
docs/technical/
├── index.html (Hub with links to all technical docs)
├── LOGIN_SIGNUP_TECHNICAL.html (System: Authentication)
├── WORKOUT_PROGRAMS_TECHNICAL.html (System: Program generation)
├── WORKOUT_TRACKING_TECHNICAL.html (System: Tracking)
├── ANALYTICS_TECHNICAL.html (System: Progress analytics)
└── [SYSTEM]_TECHNICAL.html
```

### Writing Technical Documentation

**Format**: HTML with embedded CSS and syntax-highlighted code blocks  
**Tone**: Precise, detailed, reference-focused

**HTML Structure for each system**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>[System Name] Technical Documentation - MyGym</title>
    <style>
        /* Consistent styling — see LOGIN_SIGNUP_TECHNICAL.html for reference */
    </style>
</head>
<body>
    <header>
        <h1>⚙️ [System Name] Technical Documentation</h1>
    </header>

    <nav>
        <!-- Quick navigation to main sections -->
    </nav>

    <div class="content">
        <h2 id="overview">Overview</h2>
        <!-- What system does and why -->

        <h2 id="architecture">Architecture</h2>
        <!-- Components, diagrams, flow -->
        <div class="diagram">/* ASCII diagram */</div>

        <h2 id="endpoints">API Endpoints</h2>
        <div class="endpoint">
            <strong>POST /api/v1/resource</strong>
            <div class="code-block">/* Code example */</div>
        </div>

        <h2 id="models">Models & Schemas</h2>
        <!-- Database models and Pydantic schemas -->

        <h2 id="implementation">Implementation Details</h2>
        <div class="code-block">/* Code samples */</div>

        <h2 id="dataflow">Data Flow</h2>
        <!-- Step-by-step operations -->

        <h2 id="testing">Testing</h2>
        <!-- Test patterns and coverage -->

        <h2 id="deployment">Deployment Considerations</h2>
        <!-- Environment, security, monitoring -->

        <h2 id="troubleshooting">Troubleshooting</h2>
        <div class="troubleshooting-item">
            <strong>❌ Symptom</strong>
            <p>Cause and fix</p>
        </div>

        <h2 id="references">References</h2>
        <!-- Links and citations -->
    </div>
</body>
</html>
```

**Styling Guidelines**:
- Use color scheme: `#2a5298` (primary), `#1e3c72` (secondary)
- Syntax-highlight code blocks (see LOGIN_SIGNUP_TECHNICAL.html template)
- Include ASCII flow diagrams in styled containers
- Use `.endpoint`, `.code-block`, `.diagram`, `.troubleshooting-item` classes
- Add navigation links for long documents
- Responsive design with `max-width: 1000px`
- Reference existing `LOGIN_SIGNUP_TECHNICAL.html` for style template

**Content Guidelines**:

- Include code examples (actual implementations, not pseudo-code)
- Reference specific file paths (`backend/app/models/user.py`)
- Link to related technical docs
- Document "why" decisions were made
- Include diagrams for complex flows
- Cover edge cases and error scenarios
- Explain security implications

**Examples**:

✅ Good: "Uses SHA-256 pre-hashing for passwords > 72 bytes because bcrypt has a 72-byte limit. See `hash_password()` in `backend/app/core/security.py:14`"

✅ Good: Shows actual API endpoint with request/response examples

✅ Good: Includes data flow diagram with numbered steps

### Updating Technical Docs Index

When creating a new technical doc, update `docs/technical/index.html`:

```html
<h2>Category</h2>
<ul>
    <li><a href="SYSTEM_TECHNICAL.html">System Name</a> - Brief description</li>
</ul>
```

And add quick-link card:

```html
<div class="doc-sections">
    <a href="SYSTEM_TECHNICAL.html">🔧 System Name</a>
</div>
```

---

## Shared Documentation

**Location**: `docs/` (root level)

### Guidelines

- **DATABASE_MIGRATIONS.md** — Alembic workflows, best practices
- **UV_SETUP.md** — Package manager configuration
- **README.md** — Central hub with quick-start by role

These are used by multiple audiences (users, developers, DevOps) so write clearly with multiple perspectives.

---

## Index Files & Navigation

### Main Page (`docs/index.html`)

**Primary user-facing page** — app overview + feature links:
- MyGym app description and value proposition
- Feature grid with cards (current features + coming soon)
- Discrete navigation links to technical docs in footer
- User-friendly purple gradient theme

Update when:
- Adding a new user-facing feature
- Adding "coming soon" placeholders
- Updating app description

**Note**: This page IS the user documentation hub. Feature-specific guides link back to this main page.

### Section Indexes (`docs/user/index.html`, `docs/technical/index.html`)

Secondary hubs organized by audience:

**User Docs Index** (`docs/user/index.html`):
- Links to all user feature guides
- Grouped by feature category
- Quick reference cards

**Technical Docs Index** (`docs/technical/index.html`):
- Links to all technical system docs
- Grouped by system/component
- Developer and DevOps focused

Update when:
- Adding a new doc to that section
- Reorganizing docs within section
- Adding "coming soon" placeholders

### Central README (`docs/README.md`)

Quick navigation by role:
- "I'm a user..."
- "I'm a developer..."
- "I'm DevOps..."
- Full documentation index table
- Troubleshooting quick reference

Update when:
- Adding major new documentation
- Changing documentation structure
- Adding new quick-reference sections

---

## Documentation Checklist

When creating **user documentation**:

- [ ] Written in friendly, non-technical language
- [ ] Organized as step-by-step instructions
- [ ] Includes "Before You Start" and "Troubleshooting" sections
- [ ] Added to `docs/user/index.html`
- [ ] Added to `docs/README.md` if major feature
- [ ] Links to related features
- [ ] No jargon without explanation

When creating **technical documentation**:

- [ ] Includes architecture overview/diagram
- [ ] Documents all API endpoints with examples
- [ ] References actual file paths in codebase
- [ ] Covers error handling and edge cases
- [ ] Includes testing guidance
- [ ] Documents deployment/security considerations
- [ ] Added to `docs/technical/index.html`
- [ ] Added to `docs/README.md` if major system
- [ ] Links to related systems

For **both types**:

- [ ] Clear, descriptive title
- [ ] Brief intro explaining purpose/audience
- [ ] Proper markdown formatting
- [ ] Working internal links
- [ ] References to related docs
- [ ] Last updated date or version

---

## Tools & Templates

### User Doc Template

Use `docs/user/LOGIN_SIGNUP.html` as a reference template. Key structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Feature Name] - MyGym</title>
    <style>
        /* Copy CSS from LOGIN_SIGNUP.html and customize colors if needed */
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-button">← Back</a>

        <header>
            <h1>🎯 [Feature Name]</h1>
            <p>One-line tagline</p>
        </header>

        <div class="content">
            <h2>Overview</h2>
            <p>What feature does and why</p>

            <h2>Before You Start</h2>
            <ul>
                <li>Prerequisites</li>
            </ul>

            <h2>How to [Main Action]</h2>
            <div class="step">
                <ol>
                    <li>Step...</li>
                </ol>
            </div>

            <h2>Troubleshooting</h2>
            <div class="faq-item">
                <strong>❓ Issue</strong>
                <p>Solution</p>
            </div>

            <h2>Tips & Tricks</h2>
            <ul>
                <li><div class="tip">Tip text</div></li>
            </ul>
        </div>
    </div>
</body>
</html>
```

### Technical Doc Template

Use `docs/technical/LOGIN_SIGNUP_TECHNICAL.html` as a reference template. Key structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>[System Name] Technical Documentation - MyGym</title>
    <style>
        /* Copy CSS from LOGIN_SIGNUP_TECHNICAL.html */
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚙️ [System Name] Technical Documentation</h1>
        </header>

        <nav>
            <a href="#overview">Overview</a>
            <a href="#architecture">Architecture</a>
            <a href="#endpoints">API</a>
            <a href="#models">Models</a>
            <a href="#implementation">Implementation</a>
            <a href="#dataflow">Data Flow</a>
            <a href="#testing">Testing</a>
            <a href="#deployment">Deployment</a>
            <a href="#troubleshooting">Troubleshooting</a>
            <a href="#references">References</a>
        </nav>

        <div class="content">
            <h2 id="overview">Overview</h2>
            <p>What system does and why</p>

            <h2 id="architecture">Architecture</h2>
            <div class="diagram">ASCII or flow diagram</div>

            <h2 id="endpoints">API Endpoints</h2>
            <div class="endpoint">
                <strong>POST /api/v1/resource</strong>
                <div class="code-block">
                    /* Code example with syntax highlighting */
                </div>
            </div>

            <h2 id="implementation">Implementation Details</h2>
            <div class="code-block">
                <span class="keyword">function</span> example...
            </div>

            <h2 id="troubleshooting">Troubleshooting</h2>
            <div class="troubleshooting-item">
                <strong>❌ Symptom</strong>
                <p>Cause and fix</p>
            </div>

            <h2 id="references">References</h2>
            <ul>
                <li><a href="#">Link</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
```

---

## Publishing to GitHub Pages

All documentation is automatically published to GitHub Pages. To deploy:

1. Push changes to `main` branch
2. GitHub Actions automatically builds and deploys
3. Documentation is available at `https://[username].github.io/my-gym/`

**Important**: 
- HTML files in `docs/` are served as pages
- Markdown files are viewable as GitHub markdown
- Internal links use relative paths (e.g., `../` for up, `./file.md` for same level)

---

## Examples

### User Doc Example: Login & Sign-Up
See `docs/user/LOGIN_SIGNUP.html` — includes:
- Non-technical explanation with emoji headers
- Step-by-step sign-up in styled boxes
- Step-by-step login
- Logout instructions
- Security guidance
- Troubleshooting with colored callouts
- Professional color scheme and responsive design

### Technical Doc Example: Authentication
See `docs/technical/LOGIN_SIGNUP_TECHNICAL.html` — includes:
- Architecture diagrams in styled code blocks
- API endpoint definitions with syntax highlighting
- Password hashing implementation details
- JWT token patterns
- Data flow diagrams
- Testing strategies
- Deployment considerations
- Sidebar navigation for quick access
- Syntax-highlighted code samples

---

## Quick Commands

```bash
# View documentation locally (opens in browser)
open docs/index.html

# View a specific user doc
open docs/user/LOGIN_SIGNUP.html

# View a specific technical doc
open docs/technical/LOGIN_SIGNUP_TECHNICAL.html

# Check all internal links work
grep -r 'href="' docs/ | grep -v "http" | grep -v "^Binary"

# Verify HTML syntax (if available)
html-validate docs/**/*.html

# Publish to GitHub Pages (auto-deployed from docs/ folder)
git push origin main
```

---

## Standards & Requirements

### Format Requirements
- ✅ **All documentation must be HTML** (not markdown) for GitHub Pages
- ✅ User docs use **purple gradient** theme (`#667eea`, `#764ba2`)
- ✅ Technical docs use **blue gradient** theme (`#2a5298`, `#1e3c72`)
- ✅ **Responsive design** — works on desktop, tablet, mobile
- ✅ **Styled callout boxes** — tips (green), warnings (orange), notes (blue)
- ✅ **Emoji in headers** — for visual appeal and quick scanning
- ✅ **Code syntax highlighting** — where applicable

### File Naming
- User docs: `FEATURE_NAME.html` (e.g., `LOGIN_SIGNUP.html`, `PROFILE_SETUP.html`)
- Technical docs: `SYSTEM_NAME_TECHNICAL.html` (e.g., `LOGIN_SIGNUP_TECHNICAL.html`)
- Index files: `index.html` in each directory

### Navigation
- Every HTML doc must include: back button, header, styled content, footer
- Index files must link to all docs in that section
- Related docs should link to each other

## Remember

- **Main Page First**: `docs/index.html` is the primary user-facing page with app overview and feature links
- **User Docs**: "How do I...?" → Focus on goals and tasks (non-technical)
- **Technical Docs**: "How does...work?" → Focus on implementation and integration (precise, detailed, secondary navigation)
- **HTML Only**: No markdown for feature/system docs (only shared reference docs)
- **Consistent Styling**: Use provided templates (purple for user docs, blue for technical docs)
- **Keep Updated**: Docs rot if not maintained with code changes
- **Use Examples**: Show, don't just tell
- **Index Everything**: All docs must be linked from appropriate index files
- **User-Friendly**: Professional appearance with good typography and whitespace
- **Discrete Technical Links**: Technical docs should be linked in footer, not promoted on main page
