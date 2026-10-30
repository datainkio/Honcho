---
title: Resume Template
description: Defines the foundational structure and content for all generated resumes. Editable areas (aka slots) are delineated by double braces.
created:
updated:
audience: Applicant Tracking Systems
# Placeholders. Everything in the body outside a {{ slot }} is fixed text: render it as written.
# Each {{ slot }} in the body is defined below. A slot holds words or a phrase, never a sentence
# or narrative. Its value must read correctly in the sentence around it, take its terms from the
# posting, and claim nothing the professional profile doesn't back. No < > { } or double quotes
# in a value (D9). A slot left unfilled keeps its braces, which the renderer refuses.
slots:
  job_title_article:
    filled_by: script
    source: job_title
    form: "'a' or 'an', whichever reads correctly before job_title"
  job_title:
    filled_by: script
    source: "naming.job_title(): the posting's title without the company"
    form: the posting's title exactly as written
    example: Senior UX Designer
  role_summary:
    filled_by: agent
    source: the posting's description
    form: "verb phrase that completes 'who will …'; base-form verb, no closing period"
    length: 6-15 words
    example: lead end-to-end design for a clinical data platform used by care teams
  hook_quality:
    filled_by: agent
    source: "one quality of the posting: its role, scope, industry, or a skill it asks for"
    form: "noun phrase that completes 'Given …'"
    length: 3-10 words
    example: "the role's focus on accessible public services"
  related_projects:
    filled_by: agent
    source: choose 2-3 from options; never write a new one
    form: the option as written
    options:
      - SBA.gov
      - MadeInAmerica.gov
      - Forms.gov
      - DEA.gov
      - the United States Web Design System
      - the Bixal HCD Team Playbook
      - the HCD Research Framework
      - the HCD Kickstart Dashboard
      - my work for USAID
      - my work for the USDA
      - my work with Enquos Total Health
      - my work with Seven Bridges Genomics
      - IBM's cognitive computing prototype
  common_theme:
    filled_by: agent
    source: what the posting and related_projects share per the profile
    form: "noun phrase that completes 'with its focus on …'"
    length: 2-6 words
    example: plain-language service design
---

## Contact Information

Russ Lebo
dataink.io
russell@dataink.io
+1.617.710.9566

## Summary

I am an Emmy, SXSW, and Webby award-winning digital experience designer and former educator at Harvard University and Stanford Law School. My mission in life is to design digital products and services that deliver shortcuts to insight for their users, working with teammates unafraid of iteration and who eat ambiguity for lunch. The roles I take on blend hands-on creation and research with responsibility for growing an organization's design practice.

You are looking for {{ job_title_article }} {{ job_title }} who will {{ role_summary }}. Given {{ hook_quality }}, you will find {{ related_projects }} with their focus on {{ common_theme }} to be particularly interesting.

My bona fides are below. If you prefer to read something less ATS-optimized and more digestible by humans, check out my portfolio: https://dataink.io. I look forward to hearing from you.

## Experience

### 2023 - current: Independent Contractor & Product Developer

#### Research Lead, Campaign Financing

Directed opposition research for congressional campaigns. Conducted data analysis on ten years of voter rolls at both the national and local levels paired with publicly available campaign finance records and commercial datasets of marketing and demographic data. Used network analysis tools like Gephi and Cytoscape in parallel with Tableau to produce clear, concise reports on voting behavior and campaign contributions from the state level down to individual census blocks.

#### Product Developer, Panorama

Produced Panorama, automated competitive landscape analysis tool to inform an organization's digital strategy. Researches competitors' online presence and produces a report identifying opportunities and success metrics to guide content strategy, performance targets, accessibility compliance, engagement metrics, and SEO performance.

#### Product Developer, Headhunter

Produced Headhunter, a Claude Code plugin that finds a user's ideal roles early and renders resumes, cover letters, and interest statements so they can be among the first to apply. It searches roughly 400,000 job boards and company career sites through six user-defined sources, removes duplicates, and brings forward fresh postings that match the user's target roles. A knowledge graph of the user's body of work (submitted artifacts, outcomes and research) feeds everything it generates. Topic modeling across that graph guides the user's focus when writing and identifies gaps in experience. A second graph of job descriptions grows with every search and drives ATS optimization through document structure, topic modeling and keyword matching. The user controls how much is generated, from filling slots in a fixed template to drafting from scratch, and a tailored résumé, cover letter and interest statement in several formats take minutes to produce instead of hours. Match reports and open configuration make every decision transparent.

#### Product Developer, Interrator

Produced Interrator, a lead-generating tool to help interior design firms specializing in hospitality and multi-family residential find projects before the design contract is signed. It continuously monitors publicly available municipal, state, and federal records, including permits, zoning and planning filings, and development approvals, to flag projects entering the phases when interior design firms are typically hired. Each opportunity is researched and profiled, so your team knows who the owner, developer, and architect are before making contact. Leads can be managed in the built-in CRM or exported directly to Salesforce, HubSpot, or Microsoft Dynamics 365.

### Sept 2023 - Jun 2024: Adjunct Faculty, Design Leadership Program, Johns Hopkins & Maryland Institute College of Art

Designed and led 'The Competitive Advantage', the 16-week capstone of the Design Leadership program run jointly by Johns Hopkins Business School and Maryland Institute College of Art. The class ran as one agile team in one-week sprints, with a 1:1 with each student every week. Learning outcomes included research methods, synthesis, lo-fi prototyping, Lean Startup (customer discovery, value proposition, desirability/viability/feasibility) and storytelling to stakeholders. Course modules included:

1. Design playbooks, user stories, team working agreements, team toolkits
2. Writing project, research and design briefs, each with a definition of done
3. HCD peer review modeled on pull requests
4. Paper Airplane Game (iteration) and Ball Game (story points)
5. Developing and implementing research plans: tree testing, card sorting, first-click, usability tests, and surveys; application of atomic research principles for structuring research findings
6. Anthropological methods: landscape/competitive analysis, annotated bibliographies,
   ethnography, people and artifact journeys
7. Gaps and opportunities in accessible design
8. Civic tech and judicious innovation
9. The Minimum Testable Product, MVP, and confirmation bias

### Mar 2021 - Nov 2023: Design Manager, Federal Projects, Bixal

Directed Bixal's design strategies for all projects with the company's federal clients: USAID, the DEA, the General Services Administration (and Technology Transformation Services), the Small Business Administration, Health and Human Services, and the Social Security Administration.

Coached, managed, and mentored a cross-functional team of seven designers, researchers, and engineers, each focused on its area of responsibility and operating as part of autonomous, cross-functional thematic pods. Together, we helped our government customers accelerate their digital transformations with high-visibility, high-impact projects.

Took accountability for the creative vision and the standard of output for every team. I also guided them to see inclusive design as a launchpad for innovation. Because of me, they learned to recognize the diverse needs of audiences and worked to bring underinvested communities to the forefront of the design process.

Defined and communicated the impact of HCD across a range of programs at Bixal. My goal for 2022 was to see HCD principles and practices embedded throughout all of the company's divisions. My plan for getting there centered on raising the capacity of the HCD division to provide internal support to other practices.

Consulted and coached process owners, division heads, and frontline staff on process improvement tools and methods. The HCD playbook I developed provided a domain-agnostic framework for maintaining a people-first focus throughout the lifecycle of any project. The new Community of Practice was a resource open to anyone looking to apply HCD principles to their own practice.

Directed the research and design for all federal contracts. Through oral, written, and visual presentations and collaborative workshops, I introduced Bixal's most important clients to what makes a person's experiences more intuitive, accessible, cost-effective.

- **6 direct reports**: a mix of junior and senior HCD designers and researchers
- **$65.5M**: the total value of federal contracts for which I led design and research

#### Projects

**SBA.gov**

Worked with the Small Business Administration to turn SBA.gov into a service-oriented website for the country's 32.5 million entrepreneurs and business owners.

- **320,000:** Daily visitors to sba.gov when I left the project, an increase of 300% over the previous year
- **18 languages:** Multilingual support offered by sba.gov

**MadeInAmerica.gov**

Collaborated with the General Services Administration (GSA) and the White House to increase transparency into the decisions behind $4.2B in waivers and exceptions to import and export policies.

- **$4.2 billion**: 400% increase in waivers and exemptions following the launch of my madeinamerica.gov project

**Forms.gov**

Collaborated with GSA's Office of Evaluation Scientists to build their testing capacity and improve equitable access to critical government resources for marginalized communities and populations. Used journey mapping for domain expertise and communicating design decisions.

- **107 billion:** Annual federal form submissions impacted by my collaboration with the Office of Evaluation Sciences
- **1.43 billion:** Total reduction in annual taxpayer burden when my testing tool for Forms.gov produces just a 1% improvement in completion rates

**DEA.gov**

Led research, design, and content strategy for five concurrent projects and transformed the online voice of the nation's largest law enforcement organization.

- **235,000**: Average weekly visitors to my redesign of dea.gov and its outreach sites, an increase of 21% from the year before

**Bixal.com**

Directed the transformation of Bixal's online presence during a time of heavy churn within the company. Played the roles of product owner, project manager, scrum master, lead designer, lead content strategist, and occasionally papa bear.

- **17%**: The increase in conversion rate for site visitors initiating the job application process.

#### Initiatives

**Bixal HCD Strategy 2022**

Developed the HCD component of Bixal's 2022 business strategy, laying out a plan to grow the division, attract new business, and provide greater internal support.

**The Design Lead's Playbook**

Developed a set of seven plays for maintaining HCD principles and practices throughout the lifecycle of projects.

**HCD Research Framework**

Applied the Atomic Design approach to structuring how organizations conduct HCD research. The outcome improved the analysis, sharing, and implementation of the knowledge generated by user research wherever the framework was used.

**Bixal Diversity & Inclusion Council**

Represented the HCD division in the first year of Bixal's new Diversity & Inclusion Council. Informed hiring practices and planned events celebrating the cultural identities of employees across the entire organization.

**Bixal HCD Community of Practice**

Together with two great colleagues - Will Weems and Sofya Savkina - established the first CoP for HCD at Bixal. The CoP provided expertise and guidance across Bixal, helping other departments identify opportunities to improve workflows and deliverables through design critiques, usability testing, and rapid prototyping.

**Peer Review Agreement**

Led the design and implementation of a working agreement for cross-functional teams. Informed by research, it facilitated closer collaboration across practice areas. It raised the quality of our work and reduced turnaround time, producing happier, more confident clients.

#### Presentations

**To Design & Build in the Civic Space**

Part of a three-person panel on the differences between working in civic tech and working in the private sector.

**Communicating Research Findings**

For clients, an introduction to human-centered research and design. For colleagues, a workshop on effective communication and collaboration.

### Jan 2019 - Mar 2021: Senior UX Designer, Bixal

As a Senior UX Designer, my role centered on providing research and design leadership for Bixal's most visible projects. I led the planning and implementation of research studies blending qualitative and quantitative methods, and established protocols for integrating prototype testing into every design sprint.

I worked daily with cross-functional teams to understand and document the needs of audiences, to uncover actionable insights in research data, and to synthesize those actionable insights into design decisions.

#### Projects

**United States Web Design System**

Led Bixal's design team as the primary vendor in a collaboration with the General Services Administration and the office of Technology Transformation Services to build and maintain the US Web Design System. Advised on design direction for new components, component libraries and design tokens, and improved the quality of documentation for the design system for the federal government. We made it easier to build accessible, responsive, mobile-friendly government websites.

- **26 million**: People who encounter and benefit each week from my contributions to the USWDS

**USAID**

Directed simultaneous projects to grow the knowledge-sharing capabilities of the U.S. government’s primary global hunger and food security initiative - Feed the Future - managed by USAID’s Bureau for Food Security. It operated across multiple countries (e.g., Ghana, Kenya, Bangladesh, Guatemala) with hundreds of distinct activities and projects funded through USAID and partner agencies like the USDA.

- **$20 million**: New five-year contract engaging Bixal as the primary vendor for USAID's Feed the Future program

**United States Department of Agriculture**

Directed the transformation of the USDA's strategy for communicating critical information about food recalls and the science behind food safety, as well as guiding international trade agreements. Led qualitative and quantitative research into public and private audiences through participant observation, interviews, surveys, existing market research, and natural language processing of call center transcripts. Creating high-fidelity prototypes in Drupal produced systemic improvements in the site's new information architecture.

- **7 million:** Annual reductions in cases of foodborne illness following my redesign of fsis.usda.gov
- **8%**: Reduction in reported foodborne illnesses in the year following the launch of the new fsis.usda.gov

#### Initiatives

**Human-Centered Design Brief**

Created in InVision and later ported to Figma, a living document that evolves with each sprint, communicating progress to clients and internal stakeholders and maintaining the north star for project teams. Reduced confusion over direction, specifications, and roadmapping, and reduced onboarding time for team members. Adopted by Bixal's HCD division.

**HCD Kickstart Dashboard**

A plug-and-play set of analytics visualizations tailored to the needs of HCD researchers on web-based projects. Reduced the time to find actionable insights during discovery from days to hours. Produced research plans informed by knowledge and measurable outcomes rather than guesstimation.

#### Presentations

**Introduction to UX**

Introduced clients to HCD practices and principles with a focus on the microeconomics of choice and learning.

**The Magic of UX**

Inspired cross-functional teams to embed HCD values in their processes by introducing concepts such as perceived experience, the fovea centralis, and information processing.

**Sonification & Universal Design**

An introduction to alternative methods for increasing the accessibility of insights into complex datasets for all user communities regardless of visual impairment.

**Natural Language Processing, Topic Modeling, & Information Needs**

An introduction to using machine learning for discovering actionable insights hidden within the long tail of search query analysis of federal websites.

### Nov 2016 - Aug 2018: Product Design & UX Lead, Enquos Total Health

Directed product strategy, research, testing, and visual design for a primarily mobile product. Projects ranged from research tools for evaluating the efficacy of new interventions for pain management to iOS and Android mobile applications that let consumers manage their health and fitness data. Used insights from analytics and a blend of quantitative and qualitative research methods to document and guide the development of user flows surrounding nutrition and fitness management.

### Feb 2015 - Feb 2016: Product Design & UX Lead, IBM

Led research, design, and execution of IBM's first prototype for applying AI (cognitive computing) to healthcare, a clinical decision-support app for iPad tablets.

### Sept 2014 - Jun 2015: Fellow in New Media & Human Rights, Stanford Human Rights Center

Advised graduate students on the continuously evolving relationship between information technology and human rights.

### Feb 2012 - Mar 2015: Product Design & UX Lead, Seven Bridges Genomics

Collaborated with Harvard Stem Cell Institute to research, design, and test the first commercially successful suite of cloud-based enterprise SaaS analytics tools for next-generation genomic sequencing analysis. Shaping its product strategy required systems thinking to understand the domain, workflows, and language. My work was recognized with a Best in Show award from the Bio-IT conference and as a finalist for Amazon Web Services Cloud Computing.

### Aug 2010 - Jul 2013: Adams New Media Tutor, Harvard University

Advised undergraduate students on product strategy, product design, product development, and entrepreneurship.

### Aug 2010 - Feb 2012: Rich Interactive Application Developer, IBM Interactive

Led research and design for high-visibility projects democratizing access to insights into complex bodies of data, from the product strategy and analytics for CityForward, IBM's civic data platform, to rich interactive experiences for global brands, banking and financial services clients, scientists, and researchers.

### Apr 2007 - Aug 2009: Lead Developer, Bluecadet Interactive

Led the development and interaction design for high-impact, high-visibility projects for museums, musicians, social institutions, and global brands, work characterized by award-winning visual design. My projects with Bluecadet were recognized with an Emmy for New Approaches to Journalism, Best Music Site by SXSW, multiple Webbies including People's Choice, and other awards.

## Education

### University of Michigan's School of Information (MSI/HCI)

Science of Information, specialization in Human-Computer Interaction (two years completed)

### Connecticut College (B.A.)

Anthropology, specialization in linguistics and information processing

## Awards & Recognition

- Emmy: News and Documentary
- SXSW Interactive: Best Music Site
- SXSW Interactive: Finalist
- Webby: People's Voice
- Webby: Corporate Responsibility
- Webby: Honorable Mention
- Webby Nomination: Best Art Site
- Webby Nomination: Best Photography
- Communication Arts Interactive Annual
- HOW Magazine: Design Annual

(Full history on request)

## Certifications

#### IBM UI/UX Designer Professional Certification, IBM, Sep 2025

- UX Research and Information Architecture, IBM, Aug 2025
- UI/UX Wireframing and Prototyping with Figma, IBM, Aug 2025
- UX/UI Design Fundamentals: Usability and Visual Principles, IBM, Aug 2025
- Introduction to Agile Development and Scrum, IBM, Aug 2025

#### UX Design Professional Certification, Google, Sep 2025

- User Experience for Social Good, Google, Apr 2025
- High-Fidelity Design and Prototyping in Figma, Google, Apr 2025
- Conducting UX Research and Test Early Concepts, Google, Apr 2025
- Building Wireframes and Low-Fidelity Prototypes, Google, Apr 2025
- The UX Design Process: Empathize, Define, and Ideate, Google, Apr 2025

#### UX Design Professional Certification, Microsoft, Sep 2025

- UX Design in Practice: Accessibility and Collaboration, Microsoft, Apr 2025
- User Interface Design and Prototyping, Microsoft, Aug 2025
- Designing for User Experience, Microsoft, Apr 2025

#### Figma, Sketch & Miro for UX Design Professional Certification, Coursera, Sep 2025

- High-Fidelity Design and User Testing with Sketch, Coursera, Aug 2025
- Discovery and Low-Fidelity Design with Sketch and Miro, Coursera, Aug 2025
- High-Fidelity Design and User Testing with Figma, Coursera, Aug 2025
- Discovery and Low-Fidelity Design with Figma, Coursera, Aug 2025

#### Product Owner Professional Certification, IBM, Sep 2025

- Generative AI: Revolutionizing the Product Owner Role, IBM, Aug 2025
- Practice Exam for Scrum.org PSPO I Certification, IBM, Aug 2025
- Product Owner: Essential Skills and Tools for Innovation, IBM, Aug 2025
- Product Owner: Communications & Stakeholder Management, IBM, Aug 2025
- Product Owner: Agile Development and Scrum, IBM, Aug 2025
- Product Owner: Unleashing the Power of Scrum, IBM, Aug 2025

#### AI Product Manager Professional Certification, IBM, Sep 2025

- Generative AI: Introduction and Applications, IBM, Aug 2025
- Product Management: Building AI-Powered Products, IBM, Aug 2025
- Generative AI: Foundation Models and Platforms, IBM, Aug 2025
- Generative AI: Prompt Engineering, IBM, Aug 2025
- Product Management: Developing and Delivering a New Product, IBM, Aug 2025
- Product Management: Initial Product Strategy and Plan, IBM, Aug 2025
- Product Management: Foundations & Stakeholder Collaboration, IBM, Aug 2025

#### Data science and development

- Tools for Data Science, IBM, Aug 2025
- Version Control with Git and GitHub, Board Infinity, Aug 2025
- Python for Data Science, AI & Development, IBM, Aug 2025
