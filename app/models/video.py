"""Video-related data models."""
from typing import Optional, List
from pydantic import BaseModel

class ThumbnailAnalysis(BaseModel):
    """Comprehensive thumbnail analysis model."""
    # Basic visual elements
    visual_style: Optional[str] = None
    setting: Optional[str] = None
    people_count: Optional[int] = None
    camera_angle: Optional[str] = None
    text_overlay_style: Optional[str] = None
    color_scheme: Optional[str] = None
    hook_elements: Optional[List[str]] = []
    confidence_score: Optional[float] = None
    
    # Enhanced storyboard-specific analysis
    composition_type: Optional[str] = None  # rule_of_thirds, center_focused, diagonal, symmetrical
    focal_point: Optional[str] = None  # what draws the eye first
    lighting_quality: Optional[str] = None  # natural, artificial, dramatic, soft, harsh
    mood_emotion: Optional[str] = None  # excited, calm, urgent, playful, professional
    brand_elements: Optional[List[str]] = []  # logos, products, branding visible
    
    # Content structure indicators
    story_stage: Optional[str] = None  # opening_hook, problem_setup, solution_reveal, result_show
    call_to_action_visible: Optional[bool] = None  # is there visible CTA
    product_prominence: Optional[str] = None  # dominant, subtle, background, none
    
    # Technical production elements
    production_quality: Optional[str] = None  # professional, semi_pro, amateur, phone_quality
    background_complexity: Optional[str] = None  # minimal, moderate, busy, chaotic
    props_objects: Optional[List[str]] = []  # visible props and objects
    
    # Audience engagement indicators
    visual_interest_level: Optional[str] = None  # high, medium, low
    scroll_stopping_power: Optional[str] = None  # strong, moderate, weak
    target_demographic: Optional[str] = None  # remaja, dewasa_muda, keluarga, profesional
    
    # Pattern recognition for storyboard
    content_category: Optional[str] = None  # tutorial, review, demo, lifestyle, entertainment
    pacing_indicator: Optional[str] = None  # fast_paced, moderate, slow_build
    transition_style: Optional[str] = None  # smooth, jump_cut, fade, dynamic

class VideoMetadata(BaseModel):
    """Complete video metadata model."""
    url: str
    platform: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    upload_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_analysis: Optional[ThumbnailAnalysis] = None
    extracted_at: Optional[str] = None
    processing_time_ms: Optional[int] = None
    cache_hit: Optional[bool] = False