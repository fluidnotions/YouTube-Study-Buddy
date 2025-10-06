# YouTube Study Buddy - Product Development & Deployment Plan

**Document Purpose**: Strategic planning for transforming YouTube Study Buddy into a hosted SaaS product with monetization and public knowledge sharing.

---

## Table of Contents

1. [Documentation Restructuring](#1-documentation-restructuring)
2. [GitHub Pages Setup](#2-github-pages-setup)
3. [AWS Deployment Strategy](#3-aws-deployment-strategy)
4. [Monetization via Patreon](#4-monetization-via-patreon)
5. [MCP Integration for User File Access](#5-mcp-integration-for-user-file-access)
6. [Public Obsidian Vault Hosting](#6-public-obsidian-vault-hosting)
7. [Security & Privacy Considerations](#7-security--privacy-considerations)
8. [Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Documentation Restructuring

### Current State
- `README.md` contains technical CLI documentation
- No user-facing product documentation
- No visual demonstrations of the app

### Proposed Structure

```
ytstudybuddy/
├── README.md                    # Product-focused, user-facing
├── PLAN.md                      # This file
├── docs/
│   ├── technical/
│   │   ├── cli-usage.md        # Current README content
│   │   ├── api-reference.md
│   │   └── architecture.md
│   ├── user-guide/
│   │   ├── getting-started.md
│   │   ├── streamlit-interface.md
│   │   ├── features.md
│   │   └── screenshots/
│   └── index.md                # GitHub Pages homepage
├── .github/
│   └── workflows/
│       └── deploy-pages.yml    # Auto-deploy to GitHub Pages
```

### New README.md Focus

**Target Audience**: Educators, students, content creators, researchers

**Key Sections**:
1. **What is YouTube Study Buddy?** - Educational concept & value proposition
2. **Live Demo** - Link to hosted Streamlit app on AWS
3. **Key Features** - Visual showcase (screenshots/GIFs)
4. **Use Cases** - Real-world examples
5. **Try It Now** - Link to Patreon signup
6. **Documentation** - Link to GitHub Pages
7. **Community** - Public Obsidian vault showcase

**What to Extract from Current README**:
- The educational philosophy (transform passive watching → active learning)
- Feature benefits (not implementation details)
- Example use cases
- Visual outputs (study notes structure)

---

## 2. GitHub Pages Setup

### Overview
GitHub Pages can host static sites from your repo for free.

### Setup Steps

1. **Enable GitHub Pages**
   - Go to repo Settings → Pages
   - Source: GitHub Actions (recommended) OR `gh-pages` branch
   - Choose theme or custom Jekyll/Hugo site

2. **Documentation Site Options**

   **Option A: Jekyll (GitHub's default)**
   - Pros: Zero config, automatic deployment
   - Cons: Limited customization
   - Setup: Add `_config.yml`, create markdown files in `docs/`

   **Option B: MkDocs (Recommended for technical docs)**
   - Pros: Beautiful documentation, easy navigation, search
   - Cons: Requires GitHub Actions workflow
   - Setup: `mkdocs.yml` + GitHub Actions deploy
   - Example: https://squidfunk.github.io/mkdocs-material/

   **Option C: Docusaurus (Facebook's docs framework)**
   - Pros: Modern, React-based, powerful
   - Cons: More complex setup
   - Best for: Large-scale documentation

3. **Streamlit App Screenshots**
   - Add to `docs/user-guide/screenshots/`
   - Reference in documentation
   - Consider GIF recordings for feature demonstrations

### GitHub Pages URL Format
- `https://<username>.github.io/<repo-name>/`
- Example: `https://fluidnotions.github.io/YouTube-Study-Buddy/`

### Custom Domain (Optional)
- Register domain (e.g., `ytstudybuddy.com`)
- Add CNAME file to docs
- Configure DNS settings
- Cost: ~$12/year for domain

---

## 3. AWS Deployment Strategy

### Architecture Options

#### Option A: EC2 Instance (Simple, Full Control)
**Cost**: ~$10-30/month (t3.micro/small)

**Stack**:
- EC2 instance (Ubuntu)
- Nginx reverse proxy
- Streamlit app
- Docker containers (app + tor-proxy)
- SSL via Let's Encrypt (free)

**Pros**:
- Full control
- Easy to debug
- Can run background tasks

**Cons**:
- Manual scaling
- Server management required
- Single point of failure

**Setup Steps**:
1. Launch EC2 instance (t3.micro for testing, t3.small for production)
2. Install Docker, docker-compose
3. Clone repo, setup environment
4. Configure security groups (ports 80, 443, 8501)
5. Setup Nginx → Streamlit reverse proxy
6. Configure SSL with certbot
7. Setup systemd service for auto-restart

#### Option B: AWS ECS Fargate (Serverless Containers)
**Cost**: ~$20-50/month (pay per use)

**Pros**:
- Auto-scaling
- No server management
- High availability

**Cons**:
- More complex setup
- Higher learning curve
- Harder to debug

#### Option C: AWS App Runner (Easiest)
**Cost**: ~$25-40/month

**Pros**:
- Deploy directly from GitHub
- Automatic HTTPS
- Auto-scaling
- Minimal configuration

**Cons**:
- Less control
- Limited to web apps
- Tor proxy might be challenging

### Recommended: Start with EC2, Migrate to App Runner

**Phase 1**: EC2 for MVP testing
**Phase 2**: App Runner for production scale

### Domain & SSL
- Register domain via Route 53 or external (Namecheap, Google Domains)
- Point domain to EC2 elastic IP or load balancer
- SSL certificate via AWS Certificate Manager (free) or Let's Encrypt

---

## 4. Monetization via Patreon

### Integration Strategy

#### Authentication Flow
1. User visits hosted app
2. Landing page: "Sign in with Patreon to access"
3. OAuth flow authenticates user
4. Check Patreon tier/subscription status
5. Grant access based on tier

#### Patreon API Integration

**Required**:
- Patreon OAuth app (create at patreon.com/portal/registration/register-clients)
- API keys (Client ID, Client Secret)
- Webhook for real-time subscription updates

**Implementation Options**:

**Option A: Streamlit + Session State**
```python
# Pseudo-code structure
if not st.session_state.get('authenticated'):
    show_patreon_login_button()
else:
    show_app_interface()
```

**Option B: Separate Auth Service**
- Flask/FastAPI auth service
- Issues JWT tokens
- Streamlit validates tokens
- More secure, scalable

**Patreon Tiers Example**:
- **$5/month**: 10 videos/month, basic features
- **$10/month**: 50 videos/month, all features
- **$20/month**: Unlimited, priority support, API access

### Technical Components Needed

1. **Patreon OAuth Library**: `patreon-python` or custom OAuth2
2. **Session Management**: Store auth tokens securely
3. **Rate Limiting**: Track usage per user (Redis/DynamoDB)
4. **Database**: User → Patreon ID mapping (PostgreSQL/DynamoDB)

### Limitations to Consider
- Can't actually restrict Claude API usage (your API key)
- Solution: Rate limit requests per user
- Track: videos processed, API calls made
- Reset monthly based on Patreon billing cycle

### Alternative: One-Time Purchase
- Gumroad for selling "lifetime access" codes
- Simpler than subscription management
- Less recurring revenue

---

## 5. MCP Integration for User File Access

### Understanding MCP (Model Context Protocol)

**What is MCP?**
- Protocol for connecting AI assistants to external data sources
- Developed by Anthropic
- Allows Claude to read/write files, access databases, etc.

### Your Idea: MCP File System Access

**Concept**: Users grant MCP access to their local Obsidian vault folder, app writes notes directly.

### Technical Reality Check

#### ✅ Feasible Scenarios:

**Option A: MCP Desktop Client (User Runs Locally)**
- User downloads your app
- Runs locally with MCP server
- App writes to local Obsidian vault
- **Pros**: Full file access, no network transfer
- **Cons**: Not SaaS, requires local installation

**Option B: Browser File System API**
- Web app requests file system access (Chrome/Edge only)
- Write directly to user's downloads/selected folder
- **Pros**: Works in browser
- **Cons**: Limited browser support, user must grant permission each time

**Option C: Cloud Obsidian Sync Integration**
- Obsidian Sync has API (limited)
- Write notes to Obsidian Sync cloud
- Syncs to user's vault
- **Pros**: True cloud integration
- **Cons**: Requires Obsidian Sync subscription ($4-8/month per user)

#### ❌ Not Feasible:

- **Web app writing directly to user's local filesystem** - Browser security prevents this
- **MCP accessing local files from cloud app** - MCP requires local agent

### Recommended Approach

**For SaaS Version**:
1. **Download Generated Files**
   - User processes videos
   - Downloads .md files in a ZIP
   - Manually adds to Obsidian vault

2. **Obsidian Sync API Integration** (future enhancement)
   - Partner with Obsidian
   - Or build unofficial integration
   - Automatically sync to user's vault

3. **GitHub Gist/Repo Auto-Commit**
   - Create private GitHub repo per user
   - Auto-commit new notes
   - User sets up Obsidian Git plugin to sync
   - **Pros**: Free, automated, version control
   - **Cons**: Requires user setup

**For Local/Desktop Version**:
- Build Electron app with MCP integration
- Full local file access
- Write directly to Obsidian vault
- Sell as desktop product separate from SaaS

### MCP Resources
- MCP Specification: https://modelcontextprotocol.io/
- Anthropic MCP Servers: https://github.com/anthropics/anthropic-quickstarts
- File system MCP server example: Check Anthropic's examples

---

## 6. Public Obsidian Vault Hosting

### Concept
Host your personal study notes vault publicly as a showcase and learning resource.

### Obsidian Publish (Official)
**Cost**: $8/month per site

**Pros**:
- Official solution
- Beautiful, built-in
- Search, graph view, backlinks
- Custom domain support

**Cons**:
- Recurring cost
- Limited customization

**Best For**: Professional showcase

### GitHub Pages Alternatives (FREE)

#### Option A: Obsidian Digital Garden
**Tool**: https://github.com/oleeskild/obsidian-digital-garden

**Features**:
- Free GitHub Pages hosting
- Publish vault as static site
- Graph view, backlinks
- Automatic deployment

**Setup**:
1. Install Digital Garden plugin in Obsidian
2. Configure GitHub repo
3. Mark notes as "published"
4. Plugin auto-deploys to GitHub Pages

**Example**: https://digital-garden-example.vercel.app/

#### Option B: Quartz (Recommended)
**Tool**: https://quartz.jzhao.xyz/

**Features**:
- Modern, fast static site
- Full-text search
- Graph visualization
- Dark mode
- Customizable themes
- Free on GitHub Pages

**Setup**:
```bash
git clone https://github.com/jackyzha0/quartz.git
cd quartz
npm install
# Copy your vault to content/
npx quartz build --serve
```

Deploy to GitHub Pages with Actions.

**Example**: https://quartz.jzhao.xyz/ (the docs site itself)

#### Option C: MkDocs + Obsidian
**Tool**: MkDocs with Material theme

**Process**:
1. Export Obsidian vault as markdown
2. Organize in MkDocs structure
3. Deploy via GitHub Actions

**Pros**: Full control, beautiful
**Cons**: Manual sync needed

### Recommended: Quartz for Public Vault

**Why Quartz?**
- Free
- Best balance of features/ease
- Active development
- Great for technical/educational content
- Graph view shows knowledge connections

**Your Vault Setup**:
1. Create separate repo: `ytstudybuddy-knowledge-vault`
2. Store sample study notes there
3. Use Quartz to publish to GitHub Pages
4. Link from main README

**Vault Content Ideas**:
- Sample study notes from various subjects
- "Featured" notes showcasing app capabilities
- Learning paths (connected note sequences)
- Your own educational content

### Privacy Considerations
- Only publish sanitized, curated notes
- Don't publish personal notes
- Can have private vault + public showcase vault
- Use `.gitignore` for private notes

---

## 7. Security & Privacy Considerations

### User Data
**What you collect**:
- YouTube URLs processed
- Generated study notes
- User preferences (subject, settings)
- Patreon ID (for auth)

**What you DON'T store**:
- Video transcripts (temporary processing only)
- User's personal notes/annotations
- Browse history

### Data Protection

#### GDPR Compliance (if EU users)
- Privacy policy required
- Cookie consent
- Right to deletion
- Data export functionality

#### Security Measures
1. **Environment Variables**
   - Never commit API keys
   - Use AWS Secrets Manager or .env files

2. **User Isolation**
   - Each user's files stored separately
   - Can't access other users' notes

3. **API Key Protection**
   - Your Claude API key is server-side only
   - Rate limit per user to prevent abuse
   - Monitor costs, set billing alerts

4. **Patreon OAuth**
   - Use OAuth2 (never store passwords)
   - Rotate tokens regularly
   - Validate webhook signatures

### Cost Protection

**Critical**: Users can abuse your Claude API key

**Mitigation**:
1. **Hard Limits**
   - Max videos/month per tier
   - Max transcript length (e.g., 1 hour videos only)
   - Request throttling

2. **Monitoring**
   - AWS CloudWatch for API usage
   - Alert if costs spike
   - Daily/weekly budget limits

3. **Patreon Sync**
   - Verify subscription status before processing
   - Webhook updates for cancellations
   - Grace period (24h) for payment issues

### Terms of Service
Create ToS covering:
- Fair use policy
- No commercial resale of notes
- Acceptable use (no abuse, spam)
- Service availability (best effort, no SLA)

---

## 8. Implementation Roadmap

### Phase 1: Documentation & Showcase (Week 1-2)
**Goal**: Professional presentation

- [ ] Move technical README to `docs/technical/cli-usage.md`
- [ ] Write new product-focused README.md
- [ ] Create `docs/` structure
- [ ] Take screenshots of Streamlit app
- [ ] Record GIF demos of key features
- [ ] Setup GitHub Pages with MkDocs/Jekyll
- [ ] Deploy documentation site
- [ ] Create sample public Obsidian vault
- [ ] Setup Quartz for vault hosting

**Deliverables**:
- Beautiful README
- Live docs at `https://fluidnotions.github.io/ytstudybuddy/`
- Public vault showcase

### Phase 2: AWS Deployment (Week 3-4)
**Goal**: Hosted, accessible app

**Option A: Simple EC2 Route**
- [ ] Launch EC2 instance (t3.small)
- [ ] Install Docker, docker-compose
- [ ] Clone repo, configure environment
- [ ] Setup Nginx reverse proxy
- [ ] Configure SSL (Let's Encrypt)
- [ ] Test Streamlit app access
- [ ] Setup systemd service for auto-restart
- [ ] Configure CloudWatch monitoring
- [ ] Setup automatic backups

**Option B: App Runner Route**
- [ ] Create Dockerfile for Streamlit app
- [ ] Push to ECR (Elastic Container Registry)
- [ ] Create App Runner service
- [ ] Configure environment variables
- [ ] Setup custom domain
- [ ] Test deployment

**Deliverables**:
- Live app at `https://app.ytstudybuddy.com` (or similar)
- SSL secured
- Stable, auto-restarting

### Phase 3: Patreon Integration (Week 5-6)
**Goal**: Monetization & user auth

- [ ] Create Patreon OAuth app
- [ ] Setup authentication flow in Streamlit
- [ ] Create user database (DynamoDB or PostgreSQL)
- [ ] Implement session management
- [ ] Build rate limiting system (Redis)
- [ ] Setup Patreon webhooks
- [ ] Create tier-based feature gates
- [ ] Test subscription flow
- [ ] Create Patreon page with tiers
- [ ] Write privacy policy
- [ ] Write terms of service

**Deliverables**:
- Working Patreon sign-in
- Usage tracking per user
- Tiered access control

### Phase 4: Enhanced Features (Week 7-8)
**Goal**: Better UX for file management

**File Export Options**:
- [ ] Implement ZIP download of all notes
- [ ] Add "Download as PDF" option
- [ ] Create GitHub integration (auto-commit to user's repo)
- [ ] Add email delivery option
- [ ] Explore Obsidian Sync API integration

**App Enhancements**:
- [ ] Better progress tracking for batch jobs
- [ ] Email notifications when batch completes
- [ ] Note preview in-app
- [ ] Search across user's notes
- [ ] Export to other formats (Notion, Evernote)

**Deliverables**:
- Multiple export options
- Better user experience

### Phase 5: Marketing & Growth (Ongoing)
**Goal**: Attract users

- [ ] Create demo video (YouTube)
- [ ] Write blog post about the tool
- [ ] Post on Reddit (r/ObsidianMD, r/productivity, r/GetStudying)
- [ ] Create Twitter/X account for updates
- [ ] Engage with Obsidian community
- [ ] Create tutorial series
- [ ] SEO optimization for docs site
- [ ] Consider ProductHunt launch

### Alternative: Desktop App Path

If SaaS proves too complex/costly, pivot to:
- Electron desktop app
- One-time purchase (Gumroad)
- Full MCP integration for local Obsidian access
- No hosting costs
- No subscription management complexity

---

## Resource Links

### Documentation Tools
- **MkDocs**: https://www.mkdocs.org/
- **MkDocs Material Theme**: https://squidfunk.github.io/mkdocs-material/
- **Docusaurus**: https://docusaurus.io/
- **Jekyll**: https://jekyllrb.com/

### Obsidian Publishing
- **Quartz**: https://quartz.jzhao.xyz/
- **Digital Garden**: https://github.com/oleeskild/obsidian-digital-garden
- **Obsidian Publish**: https://obsidian.md/publish

### AWS Resources
- **EC2 Getting Started**: https://docs.aws.amazon.com/ec2/
- **App Runner Docs**: https://docs.aws.amazon.com/apprunner/
- **ECS Fargate Guide**: https://docs.aws.amazon.com/ecs/

### Patreon Integration
- **Patreon API Docs**: https://docs.patreon.com/
- **OAuth Setup**: https://docs.patreon.com/#oauth
- **Python Library**: https://github.com/Patreon/patreon-python

### MCP Resources
- **MCP Specification**: https://modelcontextprotocol.io/
- **Anthropic MCP Examples**: https://github.com/anthropics/anthropic-quickstarts
- **MCP Servers**: https://github.com/modelcontextprotocol/servers

### Streamlit Deployment
- **Streamlit Docs**: https://docs.streamlit.io/
- **Community Cloud** (free tier): https://streamlit.io/cloud
- **Docker Deployment**: https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker

---

## Cost Estimates

### Monthly Costs (Production)

**Infrastructure**:
- Domain name: $1/month (amortized)
- AWS EC2 (t3.small): $15-20/month
- OR AWS App Runner: $25-40/month
- Cloudflare (CDN, optional): Free tier
- **Total Infrastructure**: $15-40/month

**Services**:
- Claude API: Variable ($3-15 per 1M tokens)
  - Estimate: $50-200/month depending on usage
- Obsidian Publish (optional): $8/month
- **Total Services**: $50-210/month

**Total Monthly**: $65-250/month

**Break-even**: ~13-50 users at $5/month Patreon tier

### Free Tier Options
- GitHub Pages: Free
- Quartz publishing: Free
- Streamlit Community Cloud: Free (with limitations)
- Let's Encrypt SSL: Free

---

## Decision Points

### You Need to Decide:

1. **Deployment Method**: EC2, App Runner, or Streamlit Cloud?
   - Recommendation: Start with Streamlit Cloud (free), migrate to EC2/App Runner when profitable

2. **Obsidian Publishing**: Quartz (free) or Obsidian Publish ($8/mo)?
   - Recommendation: Quartz to start

3. **Monetization**: Patreon or one-time purchase (Gumroad)?
   - Recommendation: Patreon for recurring revenue

4. **File Delivery**: Download, GitHub, or Obsidian Sync API?
   - Recommendation: Start with download, add GitHub integration later

5. **Documentation Tool**: MkDocs, Jekyll, or Docusaurus?
   - Recommendation: MkDocs with Material theme

6. **Domain Name**: What domain to register?
   - Ideas: ytstudybuddy.com, studybuddy.app, youtube-notes.ai

---

## Next Steps

**Immediate (This Week)**:
1. Move current README to `docs/technical/`
2. Draft new product README
3. Take screenshots of Streamlit app
4. Choose documentation tool
5. Setup GitHub Pages

**Short-term (This Month)**:
1. Deploy to AWS (EC2 or Streamlit Cloud)
2. Setup custom domain
3. Create sample public vault with Quartz
4. Launch documentation site

**Medium-term (Next 2 Months)**:
1. Implement Patreon integration
2. Add user management
3. Create marketing materials
4. Launch to limited beta users

**Long-term (3-6 Months)**:
1. Collect user feedback
2. Add requested features
3. Explore desktop app version
4. Consider API access tier

---

## Questions to Research Further

1. **MCP Feasibility**: Can MCP work in a hosted web app context, or only locally?
2. **Obsidian Sync API**: Does it exist? What are the capabilities?
3. **Patreon Webhooks**: How reliable are they for real-time access control?
4. **AWS Costs**: What's the actual cost at scale (100+ users)?
5. **Legal**: Do you need LLC/business entity for selling subscriptions?
6. **Taxes**: How to handle international Patreon subscriptions?

---

## Conclusion

This is an ambitious but achievable project. The key is to **start simple and iterate**:

1. **MVP**: GitHub Pages docs + AWS deployment + manual file download
2. **V1**: Add Patreon auth + basic rate limiting
3. **V2**: Add GitHub integration for auto-sync
4. **V3**: Explore desktop app with full MCP integration

Focus on making the core experience great before adding complexity. The educational value of the tool is strong - good documentation and a working demo will attract early adopters.

Good luck! 🚀
