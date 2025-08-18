# Video Scraper Service - Backend Architecture

## Simple Backend Flow

```mermaid
graph TD
    A[Frontend] -->|POST /extract| B[FastAPI Server]
    B --> C{What to extract?}
    
    C -->|Storyboard| D[Extract Video Metadata]
    C -->|Thumbnail| E[Extract Thumbnail Image]
    C -->|Transcript| F[Extract Subtitles]
    
    D --> G[yt-dlp Library]
    E --> G
    F --> G
    
    G --> H[TikTok/Instagram]
    
    E --> I[OpenAI Vision API]
    I --> J[Thumbnail Analysis]
    
    F --> K[Parse Subtitles]
    K --> L[Clean Transcript]
    
    D --> M[Return Metadata]
    J --> N[Return Analysis]
    L --> O[Return Transcript]
    
    M --> P[JSON Response]
    N --> P
    O --> P
    
    P --> A
    
    style A fill:#fe2c55,stroke:#fff,color:#fff
    style H fill:#000,stroke:#fe2c55,color:#fff
    style I fill:#00a67e,stroke:#fff,color:#fff
```

## What the Backend Does

### 1. **Storyboard Generation**
- Takes TikTok URL
- Extracts video metadata (title, description, duration)
- Returns structured data for pattern analysis

### 2. **Thumbnail Analysis** 
- Downloads video thumbnail
- Sends to OpenAI Vision API
- Returns visual insights (style, setting, colors)

### 3. **Transcript Extraction**
- Gets available subtitles from video
- Parses and cleans the text
- Returns timestamped transcript

## How TikTok Transcript Generation Actually Works

```mermaid
graph TD
    A[TikTok Video URL] --> B[yt-dlp checks available subtitles]
    B --> C{What subtitle types exist?}
    
    C -->|Manual Captions| D[Creator uploaded .srt/.vtt file]
    C -->|Auto-Generated| E[TikTok AI generated captions]
    C -->|No Subtitles| F[No transcript available]
    
    D --> G[Download manual subtitle file]
    E --> H[Download auto-caption file]
    F --> I[Return error: No captions found]
    
    G --> J[Parse subtitle format]
    H --> J
    
    J --> K{File format?}
    K -->|SRT| L[Parse SRT timestamps]
    K -->|VTT| M[Parse WebVTT format]
    K -->|TTML| N[Parse TTML XML format]
    
    L --> O[Clean text & extract segments]
    M --> O
    N --> O
    
    O --> P[Return structured transcript]
    
    style D fill:#00ff00,stroke:#fff,color:#000
    style E fill:#ffaa00,stroke:#fff,color:#000
    style F fill:#ff0000,stroke:#fff,color:#fff
```

## TikTok Subtitle Types

### 1. **Manual Captions** (Best Quality)
- Creator manually uploaded subtitle files
- Usually in SRT or VTT format
- Perfect timing and accurate text
- Available in multiple languages

### 2. **Auto-Generated Captions** (AI-Generated)
- TikTok's AI automatically creates captions
- Generated from audio analysis
- Less accurate but still useful
- Available for most videos with clear audio

### 3. **No Captions** 
- Video has no audio or unclear speech
- Creator disabled caption generation
- Private/restricted content

## What yt-dlp Actually Downloads

When you request a TikTok video, yt-dlp can access:

```
Example subtitle files TikTok provides:
- video_id.en.srt (English manual captions)
- video_id.en.vtt (English WebVTT format)
- video_id.auto.srt (Auto-generated English)
- video_id.id.srt (Indonesian captions)
- video_id.auto.id.srt (Auto-generated Indonesian)
```

## Subtitle File Example

```srt
1
00:00:00,000 --> 00:00:03,200
Hey guys, welcome back to my channel!

2
00:00:03,200 --> 00:00:06,800
Today I'm going to show you this amazing product

3
00:00:06,800 --> 00:00:10,500
that completely changed my morning routine
```

## Why Some Videos Don't Have Transcripts

1. **No Audio**: Video is music-only or silent
2. **Unclear Speech**: Audio quality too poor for AI
3. **Private Settings**: Creator disabled captions
4. **Language Support**: TikTok doesn't support the spoken language
5. **Copyright Issues**: Audio content is copyrighted

## Tech Stack

- **FastAPI** - Web framework
- **yt-dlp** - Video extraction library  
- **OpenAI Vision** - Thumbnail analysis
- **Python** - Programming language
