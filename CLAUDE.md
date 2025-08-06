# StoryboardAI - Project Context & Implementation Guide

## Project Overview

**What we're building:** A SaaS platform that helps content creators generate video storyboards by analyzing successful TikTok/Instagram videos and applying their patterns (not content) to create original storyboards for brand endorsements.

**Core Value Proposition:** Content creators currently manually watch reference videos and create storyboards. Our tool automates this by extracting successful patterns and generating original storyboards specific to their product/campaign brief.

## Technical Stack (Microservices Architecture)

- **Frontend:** Next.js 14 with TypeScript
- **UI Kit:** RizzUI (React component library)
- **Database:** SQLite (development) / PostgreSQL (production)
- **ORM:** Drizzle ORM (lightweight, type-safe, fast)
- **Authentication:** NextAuth.js (Google OAuth)
- **AI:** OpenAI API (GPT-3.5-turbo)
- **Frontend Deployment:** Vercel
- **Database Hosting:** Vercel Postgres (production) / Local SQLite (development)
- **Video Scraper Service:** Python + FastAPI + yt-dlp
- **Scraper Deployment:** Railway, Render, or dedicated VPS
- **Frontend Architecture:** Features-first approach with shared components, hooks, utils
- **Design Approach:** Mobile-first responsive design for TikTok/Instagram content creators

## Core Features

### 1. Reference URL Input (MVP: 3 URLs max)
- Accept TikTok and Instagram video URLs only
- Validate URLs are accessible and are videos (not photos)
- Extract metadata using Python scraper service with yt-dlp

### 2. Pattern Extraction (Not Content Copying) - MVP Approach
**Current Implementation: Thumbnail + Metadata Analysis**
- **Thumbnail Analysis**: Use GPT-4V to analyze video thumbnail for:
  - Visual style (POV, flat lay, talking head, product demo)
  - Setting/background type
  - Number of people visible
  - Camera angle and composition
  - Text overlay style and positioning
  - Color scheme and mood
  - Hook elements visible in thumbnail
- **Metadata Analysis**: Extract from yt-dlp:
  - Full video description/captions (not truncated)
  - Video duration for pacing analysis
  - Title for hook pattern identification
  - Upload date and engagement metrics
- **Pattern Categories Identified**:
  - Hook type (question, visual surprise, statistic)
  - Content structure (problem/solution, before/after, tutorial)
  - Visual style patterns
  - Pacing (based on duration)
  
**Future Enhancements** (Post-MVP):
- Frame-by-frame analysis for scene transitions
- Audio transcript analysis for script patterns
- Text overlay OCR extraction

### 3. Storyboard Generation
- Combine extracted patterns with user's product brief
- Generate 2 variations with different pattern combinations
- Each storyboard includes:
  - Scene-by-scene breakdown
  - Duration for each scene
  - Visual descriptions
  - Script suggestions
  - Camera angles
  - Text overlay recommendations
- Ability to manually edit the storyboard once its generated

### 4. Progress Tracking
- Checkbox system for each scene

## Phase 2 Features (Current Implementation)

### 1. Project Management System
- **Create Projects**: Users can create named projects to organize their storyboards
- **Project Dashboard**: Central hub displaying all user projects with search/filter
- **Project Details**: Individual project pages showing all related storyboards
- **Project CRUD**: Full create, read, update, delete operations for projects

### 2. Database Integration & Persistence
- **User Data**: All projects and storyboards saved to database
- **Multi-Database Support**: SQLite for development, PostgreSQL for production
- **Data Relationships**: Projects → Storyboards → Scenes → Tasks hierarchy
- **User Authentication**: Integration with NextAuth for user management

### 3. Enhanced User Flow
- **Dashboard-First**: Landing page shows user's projects after signin
- **Project-Centric Workflow**: Generate storyboards within project context
- **Persistent Progress**: Task completion tracking saved across sessions
- **Storyboard Management**: View, edit, and manage multiple storyboard variations per project

### 4. Improved UI/UX
- **Project Cards**: Visual project overview with metadata (count, last updated)
- **Storyboard Previews**: Quick preview of storyboard content
- **Progress Indicators**: Visual completion status for scenes and tasks
- **Empty States**: Helpful prompts when no projects or storyboards exist

## Database Schema (Drizzle ORM)

### Schema Design
```sql
-- Users table (managed by NextAuth)
users (
  id: string (primary key),
  email: string (unique),
  name: string,
  image: string,
  created_at: timestamp,
  updated_at: timestamp
)

-- Projects table
projects (
  id: serial (primary key),
  user_id: string (foreign key → users.id),
  title: string (not null),
  description: text,
  status: enum ['draft', 'active', 'completed', 'archived'],
  created_at: timestamp (default now),
  updated_at: timestamp (default now)
)

-- Storyboards table (multiple per project)
storyboards (
  id: serial (primary key),
  project_id: integer (foreign key → projects.id),
  title: string (not null),
  brief: text (not null),
  reference_urls: json (array of strings),
  total_scenes: integer,
  total_duration: integer (seconds),
  pattern_source: string,
  status: enum ['generating', 'completed', 'error'],
  generated_at: timestamp (default now),
  updated_at: timestamp (default now)
)

-- Scenes table (multiple per storyboard)
scenes (
  id: serial (primary key),
  storyboard_id: integer (foreign key → storyboards.id),
  scene_number: integer (not null),
  duration: integer (seconds),
  scene_type: enum ['hook', 'content', 'cta', 'transition'],
  visual_description: text (not null),
  script: text,
  text_overlay: string,
  camera_angle: string,
  created_at: timestamp (default now),
  updated_at: timestamp (default now)
)

-- Scene tasks table (progress tracking)
scene_tasks (
  id: serial (primary key),
  scene_id: integer (foreign key → scenes.id),
  task_type: enum ['script_written', 'scene_filmed', 'audio_recorded', 'edited'],
  completed: boolean (default false),
  completed_at: timestamp,
  updated_at: timestamp (default now)
)
```

### Drizzle Configuration
```typescript
// Database connection with environment-based switching
const db = process.env.NODE_ENV === 'production' 
  ? drizzle(new Client(process.env.DATABASE_URL))  // PostgreSQL
  : drizzle(new Database(':memory:'));             // SQLite

// Type-safe queries with excellent TypeScript integration
const userProjects = await db
  .select()
  .from(projects)
  .where(eq(projects.userId, session.user.id))
  .orderBy(desc(projects.updatedAt));
```

## Updated Project Structure (Features-First with Database)

```
storyboard-ai/
├── app/                           # Next.js 14 app directory
│   ├── page.js                   # Landing page (redirects to dashboard if signed in)
│   ├── layout.js                 # Root layout with auth provider
│   ├── globals.css               # Global styles
│   ├── dashboard/
│   │   └── page.tsx             # Dashboard - project list
│   ├── projects/
│   │   ├── [id]/
│   │   │   ├── page.tsx         # Project detail page
│   │   │   └── storyboards/
│   │   │       └── [storyboardId]/
│   │   │           └── page.tsx # Storyboard view page
│   │   └── new/
│   │       └── page.tsx         # Create new project page
│   ├── signin/
│   │   └── page.tsx             # Sign in page
│   └── api/                     # API routes (App Router)
│       ├── auth/
│       │   └── [...nextauth]/
│       │       └── route.js     # NextAuth configuration
│       ├── projects/
│       │   ├── route.js         # GET /api/projects, POST /api/projects
│       │   └── [id]/
│       │       ├── route.js     # GET/PUT/DELETE /api/projects/[id]
│       │       └── storyboards/
│       │           └── route.js # POST /api/projects/[id]/storyboards
│       ├── storyboards/
│       │   └── [id]/
│       │       ├── route.js     # GET/PUT/DELETE /api/storyboards/[id]
│       │       └── scenes/
│       │           └── route.js # GET/PUT /api/storyboards/[id]/scenes
│       ├── scenes/
│       │   └── [id]/
│       │       └── tasks/
│       │           └── route.js # PUT /api/scenes/[id]/tasks
│       ├── generate-storyboard/
│       │   └── route.js         # Current storyboard generation endpoint
│       └── extract/
│           └── route.js         # Video metadata extraction (proxy to Python service)
├── features/                     # Features-first approach
│   ├── dashboard/               # Dashboard feature (NEW)
│   │   ├── components/
│   │   │   ├── ProjectCard.tsx
│   │   │   ├── ProjectGrid.tsx
│   │   │   ├── CreateProjectButton.tsx
│   │   │   └── EmptyProjectsState.tsx
│   │   ├── hooks/
│   │   │   ├── useProjects.ts
│   │   │   └── useProjectSearch.ts
│   │   └── utils/
│   │       └── projectFilters.ts
│   ├── projects/               # Project management feature (NEW)
│   │   ├── components/
│   │   │   ├── ProjectHeader.tsx
│   │   │   ├── ProjectInfo.tsx
│   │   │   ├── CreateProjectModal.tsx
│   │   │   ├── EditProjectModal.tsx
│   │   │   ├── StoryboardList.tsx
│   │   │   └── StoryboardPreview.tsx
│   │   ├── hooks/
│   │   │   ├── useProject.ts
│   │   │   ├── useCreateProject.ts
│   │   │   └── useProjectStoryboards.ts
│   │   └── utils/
│   │       ├── projectValidation.ts
│   │       └── projectFormatting.ts
│   ├── url-input/              # URL input feature (UPDATED)
│   │   ├── components/
│   │   │   ├── URLInput.tsx
│   │   │   └── URLValidator.tsx
│   │   ├── hooks/
│   │   │   └── useURLValidation.ts
│   │   └── utils/
│   │       └── urlValidation.ts
│   ├── brief-input/            # Content brief feature (UPDATED)
│   │   ├── components/
│   │   │   ├── BriefInput.tsx
│   │   │   └── BriefPreview.tsx
│   │   ├── hooks/
│   │   │   └── useBrief.ts
│   │   └── utils/
│   │       └── briefValidation.ts
│   ├── storyboard-generator/   # Storyboard generation feature (UPDATED)
│   │   ├── components/
│   │   │   ├── StoryboardView.tsx
│   │   │   ├── SceneCard.tsx
│   │   │   ├── VariationTabs.tsx
│   │   │   └── GenerateStoryboardForm.tsx
│   │   ├── hooks/
│   │   │   ├── useStoryboard.ts
│   │   │   ├── useGeneration.ts
│   │   │   └── useStoryboardPersistence.ts
│   │   └── utils/
│   │       ├── storyboardFormatting.ts
│   │       └── storyboardValidation.ts
│   └── progress-tracker/       # Progress tracking feature (UPDATED)
│       ├── components/
│       │   ├── ProgressTracker.tsx
│       │   ├── TaskCheckbox.tsx
│       │   └── ProgressIndicator.tsx
│       ├── hooks/
│       │   ├── useProgress.ts
│       │   └── useTaskUpdate.ts
│       └── utils/
│           ├── progressCalculation.ts
│           └── taskValidation.ts
├── shared/                  # Shared components, hooks, utils
│   ├── components/
│   │   ├── ui/             # RizzUI component wrappers
│   │   │   ├── Button.js   # RizzUI Button wrapper
│   │   │   ├── Input.js    # RizzUI Input wrapper
│   │   │   ├── Modal.js    # RizzUI Modal wrapper
│   │   │   ├── Card.js     # RizzUI Card wrapper
│   │   │   ├── Badge.js    # RizzUI Badge wrapper
│   │   │   ├── Avatar.js   # RizzUI Avatar wrapper
│   │   │   └── LoadingSpinner.js # RizzUI Spinner wrapper
│   │   ├── layout/
│   │   │   ├── Header.js
│   │   │   └── Footer.js
│   │   └── common/
│   │       ├── ErrorBoundary.js
│   │       └── Toast.js    # RizzUI Toast wrapper
│   ├── hooks/
│   │   ├── useLocalStorage.js
│   │   ├── useDebounce.js
│   │   └── useApi.js
│   ├── utils/
│   │   ├── api.js
│   │   ├── cache.js
│   │   ├── validation.js
│   │   └── formatters.js
│   └── constants/
│       ├── api.js
│       └── validation.js
├── lib/
│   ├── db/                      # Database layer (NEW)
│   │   ├── index.ts            # Drizzle database connection
│   │   ├── schema.ts           # Database schema definitions
│   │   ├── migrations/         # Database migration files
│   │   └── queries/            # Database query functions
│   │       ├── projects.ts     # Project-related queries
│   │       ├── storyboards.ts  # Storyboard queries
│   │       ├── scenes.ts       # Scene queries
│   │       └── users.ts        # User queries
│   ├── auth/                    # Authentication (NEW)
│   │   ├── config.ts           # NextAuth configuration
│   │   ├── providers.ts        # Auth providers (Google, etc.)
│   │   └── middleware.ts       # Auth middleware
│   ├── openai.ts               # OpenAI integration (UPDATED)
│   ├── videoExtractor.ts       # yt-dlp wrapper (UPDATED)
│   ├── patterns.ts             # Pattern analysis logic (UPDATED)
│   └── utils.ts                # Utility functions
├── public/                   # Static assets
├── .env.local               # Environment variables
├── package.json
└── README.md
```

## Current API Architecture

### Storyboard Generation Flow
The current implementation uses a dedicated storyboard generation service (`/lib/ai/storyboard-generator.ts`) that:

1. **Extracts Video Metadata**: Uses the Python FastAPI service to extract video metadata and thumbnail analysis
2. **Analyzes Patterns**: Processes the extracted data to identify successful content patterns
3. **Generates Storyboards**: Uses OpenAI GPT-4 to create contextual storyboards in Indonesian
4. **Returns Structured Data**: Provides detailed scene breakdowns with visual descriptions, scripts, and production notes

### Next.js Frontend API Routes
```javascript
// Authentication
GET    /api/auth/[...nextauth] // NextAuth.js authentication endpoints

// Projects Management
GET    /api/projects           // List user's projects
POST   /api/projects           // Create new project
GET    /api/projects/[id]      // Get project details with storyboards
PUT    /api/projects/[id]      // Update project (title, description, status)
DELETE /api/projects/[id]      // Delete project and all associated data

// Storyboard Management (within projects)
POST   /api/projects/[id]/storyboards    // Generate new storyboard for project
GET    /api/storyboards/[id]             // Get specific storyboard with scenes
PUT    /api/storyboards/[id]             // Update storyboard details
DELETE /api/storyboards/[id]             // Delete storyboard

// Scene Management
GET    /api/storyboards/[id]/scenes      // Get all scenes for storyboard
PUT    /api/scenes/[id]                  // Update scene details
PUT    /api/scenes/[id]/tasks            // Update scene task completion

// Direct Storyboard Generation
POST   /api/generate-storyboard        // Generate storyboard with reference URLs and brief

// Utility
POST   /api/extract            // Video metadata extraction (proxy to Python service)

// Response Format (All endpoints follow this pattern)
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2024-03-15T10:30:00Z",
    "user_id": "user_123",
    "request_id": "req_abc123"
  }
}
```

### Database Query Patterns (Drizzle)
```typescript
// Example: Get user projects with storyboard counts
const projectsWithCounts = await db
  .select({
    id: projects.id,
    title: projects.title,
    description: projects.description,
    status: projects.status,
    createdAt: projects.createdAt,
    updatedAt: projects.updatedAt,
    storyboardCount: count(storyboards.id),
  })
  .from(projects)
  .leftJoin(storyboards, eq(projects.id, storyboards.projectId))
  .where(eq(projects.userId, userId))
  .groupBy(projects.id)
  .orderBy(desc(projects.updatedAt));

// Example: Get project with all storyboards and scenes
const projectWithStoryboards = await db
  .select()
  .from(projects)
  .where(and(eq(projects.id, projectId), eq(projects.userId, userId)))
  .with({
    storyboards: db
      .select()
      .from(storyboards)
      .where(eq(storyboards.projectId, projectId))
      .with({
        scenes: db
          .select()
          .from(scenes)
          .where(eq(scenes.storyboardId, storyboards.id))
          .orderBy(scenes.sceneNumber)
      })
  });
```

### Python Scraper Service API (FastAPI)

#### Endpoints Overview
```python
# FastAPI service endpoints with status codes

POST   /extract                # Extract single video metadata
POST   /extract/batch          # Extract multiple videos (max 3)
GET    /health                 # Health check
GET    /supported-platforms    # List supported platforms
GET    /stats                  # Service statistics
```

#### API Response Standards
All responses follow RESTful conventions with proper HTTP status codes:

**Success Codes:**
- `200 OK` - Request successful
- `201 Created` - Resource created
- `202 Accepted` - Request accepted for processing

**Error Codes:**
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing/invalid API key
- `422 Unprocessable Entity` - Valid request but processing failed
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

#### Detailed Endpoint Documentation

**POST /extract**

*Request:*
```json
{
  "url": "https://www.tiktok.com/@user/video/123456789",
  "include_thumbnail_analysis": true,
  "cache_ttl": 3600
}
```

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "url": "https://www.tiktok.com/@user/video/123456789",
    "platform": "tiktok",
    "title": "5 minute morning routine that changed my life",
    "description": "Start your day right with these simple habits #morningroutine #productivity #selfcare",
    "duration": 23,
    "view_count": 2500000,
    "like_count": 45000,
    "comment_count": 1200,
    "share_count": 8500,
    "upload_date": "2024-03-10",
    "thumbnail_url": "https://p16-sign.tiktokcdn.com/tos-maliva-p-0068/...",
    "thumbnail_analysis": {
      "visual_style": "talking_head",
      "setting": "modern_bedroom",
      "people_count": 1,
      "camera_angle": "medium_close_up",
      "text_overlay_style": "clean_white_on_dark",
      "color_scheme": "warm_bright_tones",
      "hook_elements": ["coffee_cup", "surprised_expression"],
      "confidence_score": 0.87
    },
    "extracted_at": "2024-03-15T10:30:00Z",
    "processing_time_ms": 3420,
    "cache_hit": false
  },
  "metadata": {
    "request_id": "req_abc123",
    "api_version": "1.0.0",
    "rate_limit": {
      "remaining": 59,
      "reset_at": "2024-03-15T11:00:00Z"
    }
  }
}
```

*Error Response (422 Unprocessable Entity):*
```json
{
  "success": false,
  "error": {
    "code": "VIDEO_UNAVAILABLE",
    "message": "Video is private, deleted, or restricted",
    "details": {
      "url": "https://www.tiktok.com/@user/video/123456789",
      "platform": "tiktok",
      "reason": "private_video"
    }
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2024-03-15T10:30:00Z"
  }
}
```

**POST /extract/batch**

*Request:*
```json
{
  "urls": [
    "https://www.tiktok.com/@user1/video/123",
    "https://www.instagram.com/reel/ABC123/",
    "https://www.tiktok.com/@user2/video/456"
  ],
  "include_thumbnail_analysis": true,
  "parallel_processing": true
}
```

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "processed": [
      {
        "url": "https://www.tiktok.com/@user1/video/123",
        "status": "success",
        "data": { /* video metadata */ }
      },
      {
        "url": "https://www.instagram.com/reel/ABC123/",
        "status": "success",
        "data": { /* video metadata */ }
      }
    ],
    "failed": [
      {
        "url": "https://www.tiktok.com/@user2/video/456",
        "status": "failed",
        "error": {
          "code": "VIDEO_PRIVATE",
          "message": "Video is private or deleted"
        }
      }
    ],
    "summary": {
      "total_requested": 3,
      "successful": 2,
      "failed": 1,
      "processing_time_ms": 8750
    }
  },
  "metadata": {
    "request_id": "req_batch_xyz789",
    "processed_at": "2024-03-15T10:30:00Z"
  }
}
```

**GET /health**

*Success Response (200 OK):*
```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "yt_dlp": "healthy",
    "openai": "healthy",
    "redis": "healthy"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_processed": 15420,
    "cache_hit_rate": 0.73
  }
}
```

**GET /supported-platforms**

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "platforms": [
      {
        "name": "tiktok",
        "domain": "tiktok.com",
        "supported_features": [
          "metadata_extraction",
          "thumbnail_analysis",
          "engagement_metrics"
        ],
        "url_patterns": [
          "https://www.tiktok.com/@{username}/video/{video_id}",
          "https://vm.tiktok.com/{short_id}",
          "https://vt.tiktok.com/{short_id}"
        ]
      },
      {
        "name": "instagram",
        "domain": "instagram.com",
        "supported_features": [
          "metadata_extraction",
          "thumbnail_analysis",
          "basic_metrics"
        ],
        "url_patterns": [
          "https://www.instagram.com/reel/{reel_id}/",
          "https://www.instagram.com/p/{post_id}/"
        ]
      }
    ],
    "limitations": {
      "max_urls_per_batch": 3,
      "rate_limit_per_minute": 60,
      "max_video_duration": 300
    }
  }
}
```

**GET /stats**

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "service_stats": {
      "total_extractions": 150420,
      "successful_extractions": 142891,
      "failed_extractions": 7529,
      "success_rate": 0.95,
      "avg_processing_time_ms": 4250
    },
    "platform_breakdown": {
      "tiktok": {
        "count": 98765,
        "success_rate": 0.96
      },
      "instagram": {
        "count": 51655,
        "success_rate": 0.93
      }
    },
    "error_breakdown": {
      "VIDEO_PRIVATE": 3210,
      "VIDEO_DELETED": 2145,
      "PLATFORM_ERROR": 1890,
      "TIMEOUT": 284
    },
    "cache_stats": {
      "hit_rate": 0.73,
      "total_entries": 45230,
      "memory_usage_mb": 1250
    }
  },
  "generated_at": "2024-03-15T10:30:00Z"
}
```

#### Error Response Format

All error responses follow this standard format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional context specific to the error
    }
  },
  "metadata": {
    "request_id": "req_unique_id",
    "timestamp": "2024-03-15T10:30:00Z"
  }
}
```

#### Common Error Codes

- `INVALID_URL`: URL format is invalid
- `UNSUPPORTED_PLATFORM`: Platform not supported
- `VIDEO_UNAVAILABLE`: Video is private, deleted, or restricted
- `NOT_VIDEO_CONTENT`: URL contains image or non-video content instead of a video
- `VIDEO_TOO_LONG`: Video exceeds maximum duration
- `EXTRACTION_FAILED`: Technical error during extraction
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `API_KEY_INVALID`: Invalid or missing API key
- `THUMBNAIL_ANALYSIS_FAILED`: OpenAI Vision API error
- `SERVICE_UNAVAILABLE`: External service dependency down

## Key Implementation Details

### Updated Environment Variables (Phase 2)

#### Next.js Frontend (.env.local)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/storyboard_db  # Production (Vercel Postgres)
DATABASE_URL=file:./dev.db                                  # Development (SQLite)
NODE_ENV=development                                         # or production

# NextAuth.js
NEXTAUTH_SECRET=your-nextauth-secret-key
NEXTAUTH_URL=http://localhost:3000                          # or your production URL
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here

# Python Scraper Service
SCRAPER_SERVICE_URL=http://localhost:8000
SCRAPER_SERVICE_API_KEY=your-scraper-api-key

# App Config
NEXT_PUBLIC_APP_URL=http://localhost:3000
MAX_URLS_PER_REQUEST=3
MAX_PROJECTS_PER_USER=50
CACHE_TTL_HOURS=24

# Database Connection Pool (Production only)
DB_POOL_SIZE=10
DB_CONNECTION_TIMEOUT=30000
```

#### Python Scraper Service (.env)
```env
# Service Config
API_KEY=your-scraper-api-key
PORT=8000
HOST=0.0.0.0

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_EXTRACTIONS=5

# yt-dlp Config
YTDLP_CACHE_DIR=/tmp/ytdlp_cache
YTDLP_TIMEOUT=30
```

### URL Validation Rules
```javascript
// Must be from TikTok or Instagram
const validPlatforms = ['tiktok.com', 'instagram.com'];
// Format examples:
// https://www.tiktok.com/@username/video/1234567890
// https://www.instagram.com/reel/ABC123/
// Maximum 3 URLs per request
// At least 1 URL required
```

### Pattern Extraction Flow - MVP Implementation
```javascript
// 1. Next.js frontend sends URLs to /api/extract
// 2. Next.js proxy calls Python scraper service
// 3. Python service uses yt-dlp to extract:
//    - Full metadata (title, description, captions)
//    - Thumbnail URL
// 4. Python service calls OpenAI Vision API to analyze thumbnail
// 5. Return: metadata + thumbnail analysis
// 6. Next.js combines thumbnail analysis + metadata for pattern extraction
// 7. Cache results for 24 hours to avoid reprocessing

// Performance: ~10-15 seconds per video (vs 40-75s for full video analysis)
```

### API Request/Response Standards

All API responses follow a consistent format with proper HTTP status codes:

#### Success Responses
- **200 OK**: Request successful, data returned
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no content to return

#### Error Responses
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid API key
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Valid request but cannot process
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Example API Request/Response

**POST /api/generate-storyboard**

*Request:*
```json
{
  "urls": [
    "https://www.tiktok.com/@user/video/123",
    "https://www.instagram.com/reel/ABC/"
  ],
  "brief": "Create 2 reels for Roborock S8 robot vacuum. Highlight quiet operation and pet hair removal.",
  "target_audience": "Pet owners",
  "product_name": "Roborock S8",
  "key_messages": ["Quiet operation", "Pet hair removal"]
}
```

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "title": "Pet Parents, This Changes Everything!",
    "total_duration": 28,
    "pattern_source": "talking_head_morning_routine",
    "scenes": [
      {
        "scene_number": 1,
        "duration": 5,
        "scene_type": "hook",
        "visual_description": "Close-up of pet hair on carpet with frustrated pet owner",
        "script": "Masih vakum bulu hewan dua kali sehari? Ada cara yang lebih mudah!",
        "text_overlay": "2X SEHARI?! 😩",
        "camera_angle": "close_up",
        "notes": "Show relatable frustration, use warm lighting"
      },
      {
        "scene_number": 2,
        "duration": 15,
        "scene_type": "solution",
        "visual_description": "Roborock S8 cleaning efficiently while owner relaxes",
        "script": "Roborock S8 ini beda banget. Hisapannya kuat tapi suaranya hampir nggak kedengar. Bulu kucing langsung terangkat semua!",
        "text_overlay": "QUIET + POWERFUL 🔥",
        "camera_angle": "medium_shot",
        "notes": "Demonstrate product in action, emphasize quiet operation"
      },
      {
        "scene_number": 3,
        "duration": 8,
        "scene_type": "cta",
        "visual_description": "Happy pet owner with clean floor and relaxed pet",
        "script": "Sekarang rumah bersih, aku santai, kucing juga nggak stress. Link di bio ya!",
        "text_overlay": "LINK DI BIO 👆",
        "camera_angle": "wide_shot",
        "notes": "Show end result, create urgency for action"
      }
    ],
    "variation_note": "Natural Indonesian conversation style with relatable pet owner pain points"
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2024-03-15T10:30:00Z"
  }
}
```

*Error Response (400 Bad Request):*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid URLs provided",
    "details": {
      "invalid_urls": ["https://www.youtube.com/watch?v=invalid"],
      "valid_platforms": ["tiktok.com", "instagram.com"]
    }
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

**POST /api/extract**

*Request:*
```json
{
  "urls": ["https://www.tiktok.com/@user/video/123"]
}
```

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": [
    {
      "url": "https://www.tiktok.com/@user/video/123",
      "title": "5 minute morning routine that changed my life",
      "description": "Full caption here including hashtags #morningroutine #productivity...",
      "duration": 23,
      "view_count": 2500000,
      "like_count": 45000,
      "thumbnail": "https://p16-sign.tiktokcdn.com/...",
      "thumbnail_analysis": "Visual style: Talking head with bright morning lighting. Setting: Modern bedroom with minimalist decor. Camera: Medium close-up shot, slight upward angle. Text overlay: Clean white text on dark overlay. Hook elements: Person holding coffee cup with surprised expression. Color scheme: Warm, bright tones suggesting energy.",
      "platform": "tiktok",
      "extracted_at": "2024-03-15T10:30:00Z"
    }
  ],
  "metadata": {
    "processed_at": "2024-03-15T10:30:00Z",
    "processing_time_ms": 8750,
    "cache_hit": true
  }
}
```

*Error Response (422 Unprocessable Entity):*
```json
{
  "success": false,
  "error": {
    "code": "VIDEO_PRIVATE",
    "message": "Video is private or deleted",
    "details": {
      "url": "https://www.tiktok.com/@user/video/123",
      "platform": "tiktok"
    }
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

**GET /api/project/[id]**

*Success Response (200 OK):*
```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "created_at": "2024-03-15T10:30:00Z",
    "brief": "Create 2 reels for Roborock S8 robot vacuum...",
    "reference_urls": ["https://www.tiktok.com/@user/video/123"],
    "variations": [...],
    "progress": {
      "total_tasks": 16,
      "completed_tasks": 3,
      "percentage": 18.75
    }
  }
}
```

*Error Response (404 Not Found):*
```json
{
  "success": false,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "Project with ID 'proj_abc123' not found"
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

**Rate Limiting Response (429 Too Many Requests):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": 10,
      "window": "1 hour",
      "retry_after": 3600
    }
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

## Next.js Specific Implementation

### API Route Pattern (App Router)
```javascript
// app/api/generate-storyboard/route.js
import { NextResponse } from 'next/server';
import { generateStoryboard } from '@/lib/ai/storyboard-generator';

export async function POST(request) {
  try {
    // Parse and validate request body
    const { urls, brief, target_audience, product_name, key_messages } = await request.json();
    
    // Generate storyboard using service
    const result = await generateStoryboard({
      referenceUrls: urls,
      brief,
      targetAudience: target_audience,
      productName: product_name,
      keyMessages: key_messages
    });
    
    // Return response
    return NextResponse.json({
      success: true,
      data: result,
      metadata: {
        request_id: `req_${Date.now()}`,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    return NextResponse.json(
      { 
        success: false,
        error: {
          code: 'GENERATION_FAILED',
          message: error.message
        }
      },
      { status: 500 }
    );
  }
}
```

### Client-Side Fetching
```javascript
// In your React component
const generateStoryboard = async (urls, brief, options = {}) => {
  const response = await fetch('/api/generate-storyboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      urls, 
      brief,
      target_audience: options.targetAudience,
      product_name: options.productName,
      key_messages: options.keyMessages
    })
  });
  
  const result = await response.json();
  
  if (!result.success) {
    throw new Error(result.error?.message || 'Failed to generate storyboard');
  }
  
  return result.data;
};
```

### State Management (Simple)
```javascript
// Using React useState for MVP
const [urls, setUrls] = useState(['', '', '']);
const [brief, setBrief] = useState('');
const [loading, setLoading] = useState(false);
const [storyboard, setStoryboard] = useState(null);
```

## Development Workflow

### 1. Initial Setup
```bash
# Create Next.js app
npx create-next-app@latest storyboard-ai
cd storyboard-ai

# Install dependencies
npm install openai sqlite3 @vercel/postgres rizzui

# Create .env.local
echo "OPENAI_API_KEY=sk-your-key" > .env.local

# Run development server
npm run dev
```

### 2. Build Order (Mobile-First Development)
1. **Week 1 - Core Functionality**
   - Day 1-2: Setup Next.js + RizzUI, create basic mobile-first UI (320px breakpoint)
   - Day 3-4: Implement API routes for generation
   - Day 5-7: Integrate OpenAI, test with real videos

2. **Week 2 - Polish & Deploy**
   - Day 8-9: Progress tracking, error handling with RizzUI components
   - Day 10-11: Mobile optimization (touch targets, gestures), then desktop responsive
   - Day 12-13: Deploy to Vercel
   - Day 14: Launch!

### 3. Deployment Steps
```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_REPO_URL
git push -u origin main

# 2. Deploy to Vercel
# - Go to vercel.com
# - Import your GitHub repo
# - Add env variables
# - Deploy!
```

## Common Patterns to Extract

### Hook Types
- **Question Hook**: "Still doing X the old way?"
- **Stat Hook**: "87% of people don't know..."
- **Visual Surprise**: Unexpected visual in first 2 seconds
- **Problem Statement**: "I was so tired of..."

### Content Structures
- **Problem-Agitation-Solution**: Show problem → Make it worse → Present solution
- **Before/After**: Transformation showcase
- **Tutorial/How-to**: Step-by-step process
- **Testimonial**: Personal story format

## Performance Optimization

### Caching Strategy
```javascript
// Simple in-memory cache for MVP
const cache = new Map();

const getCached = (key) => {
  const item = cache.get(key);
  if (item && item.expires > Date.now()) {
    return item.data;
  }
  return null;
};

const setCached = (key, data, hours = 24) => {
  cache.set(key, {
    data,
    expires: Date.now() + (hours * 60 * 60 * 1000)
  });
};
```

### Response Times
- URL validation: < 1 second
- Pattern extraction: < 10 seconds per video
- AI generation: < 5 seconds
- Total request: < 30 seconds for 3 URLs

## Error Handling

```javascript
// Common errors to handle
const errors = {
  INVALID_URL: 'URL must be from TikTok or Instagram',
  TOO_MANY_URLS: 'Maximum 3 URLs allowed',
  BRIEF_TOO_SHORT: 'Brief must be at least 10 characters',
  VIDEO_PRIVATE: 'Video is private or deleted',
  AI_FAILED: 'Failed to generate storyboard',
  RATE_LIMITED: 'Too many requests, please try again'
};
```

## Testing Checklist

- [ ] URL validation (valid/invalid platforms)
- [ ] 3 URL limit enforcement
- [ ] Empty URL handling
- [ ] Brief validation (min/max length)
- [ ] AI response parsing
- [ ] Error states in UI
- [ ] Loading states
- [ ] Mobile responsiveness (320px, 375px, 414px breakpoints)
- [ ] Touch targets (minimum 44px)
- [ ] Swipe gestures for storyboard navigation
- [ ] Keyboard accessibility
- [ ] Screen reader compatibility
- [ ] Cache hit/miss

## AI Prompts (GPT-3.5-turbo optimized)

### Pattern Analysis Prompt
```javascript
const patternPrompt = `
Analyze these videos and identify content patterns:
${JSON.stringify(videoMetadata)}

Return JSON with:
- hook_type: question/stat/visual_surprise
- structure: problem_solution/before_after/tutorial
- pacing: fast_cuts/single_take/mixed
- avg_scene_duration: number in seconds
`;
```

### Storyboard Generation Prompt
```javascript
const storyboardPrompt = `
Create 2 TikTok/Instagram video storyboards.

Brief: ${brief}
Reference patterns: ${patterns}

Each variation needs:
- 4 scenes
- Total duration: 20-30 seconds
- Scene details: visual, script, text_overlay

Return only valid JSON. Be creative and specific to the product.
`;
```

## Cost Optimization

### Per Request Costs
- GPT-3.5-turbo: ~$0.02 per storyboard
- Vercel hosting: Free tier (100GB bandwidth)
- Total monthly cost for 1000 users: ~$20

### Optimization Tips
1. Cache video metadata for 24 hours
2. Limit brief length to 500 chars
3. Use streaming responses for better UX
4. Implement rate limiting (10 requests/hour/IP)

## Security Considerations

```javascript
// Input sanitization
const sanitizeBrief = (brief) => {
  return brief
    .trim()
    .substring(0, 500)
    .replace(/[<>]/g, '');
};

// Rate limiting (simple)
const rateLimiter = new Map();

const checkRateLimit = (ip) => {
  const key = `rate_${ip}`;
  const attempts = rateLimiter.get(key) || 0;
  
  if (attempts > 10) {
    throw new Error('Rate limit exceeded');
  }
  
  rateLimiter.set(key, attempts + 1);
  setTimeout(() => rateLimiter.delete(key), 3600000); // 1 hour
};
```

## MVP Launch Strategy

### Phase 1: Soft Launch (Week 1)
- Deploy to Vercel
- Share with 10-20 content creators
- Gather feedback
- Fix critical bugs

### Phase 2: Public Launch (Week 2)
- Post on Twitter/LinkedIn
- Submit to Product Hunt
- Reddit (r/tiktok, r/instagrammarketing)
- Monitor performance

### Phase 3: Iterate (Week 3+)
- Add most requested features
- Optimize costs
- Consider paid tier

## Questions to Address Post-MVP

1. Should we store generated storyboards?
2. User accounts vs anonymous usage?
3. Export formats (PDF, Notion, etc.)?
4. Analytics on storyboard performance?
5. Team collaboration features?

## Mobile-First Design Principles

### UI/UX Guidelines
- **Touch-First Interface**: 44px minimum touch targets
- **Thumb-Friendly Navigation**: Critical actions within thumb reach
- **Vertical Scrolling**: Primary interaction pattern
- **Swipe Gestures**: Navigate between storyboard variations
- **Progressive Enhancement**: Core functionality on mobile, enhanced on desktop

### Responsive Breakpoints
```css
/* Mobile First */
@media (min-width: 320px) { /* Small mobile */ }
@media (min-width: 375px) { /* iPhone standard */ }
@media (min-width: 414px) { /* Large mobile */ }
@media (min-width: 768px) { /* Tablet */ }
@media (min-width: 1024px) { /* Desktop */ }
```

### Component Design Patterns
- **Stacked Layout**: Vertical component arrangement on mobile
- **Collapsible Sections**: Accordion-style for content organization
- **Bottom Sheet**: Modal overlays from bottom on mobile
- **Floating Action Button**: Primary CTA positioning
- **Pull-to-Refresh**: Standard mobile gesture support

## Next Steps After MVP

1. **User Accounts** - Save storyboards, history
2. **More Platforms** - YouTube Shorts support
3. **Export Options** - PDF, Google Docs
4. **Templates** - Save successful patterns
5. **Analytics** - Track which storyboards perform
6. **Paid Tier** - More URLs, GPT-4, priority processing
7. **PWA Features** - Offline support, push notifications
