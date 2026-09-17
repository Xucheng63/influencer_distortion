export type DistortionPlatform =
  | "youtube"
  | "twitter"
  | "weibo"
  | "bluesky"
  | "reddit";

export interface DistortionPost {
  content: string;
  posted_at: string;
  distortion_types: string[];
  confidence: number;
  classification_method: string;
  trigger_signals: string[];
}

export interface DistortionProfileResult {
  account: {
    handle: string;
    display_name: string;
    platform: DistortionPlatform;
  };
  profile: {
    distortion_index: number;
    significance_inflation_rate: number;
    anxiety_manufacturing_rate: number;
    novelty_claim_rate: number;
    loaded_language_rate: number;
    temporal_distortion_rate: number;
    total_posts_analyzed: number;
  };
  posts: DistortionPost[];
}

export interface DistortionJob {
  job_id?: string;
  status: string;
  progress?: {
    done: number;
    total: number;
  };
  result?: DistortionProfileResult;
  error?: string;
  cached: boolean;
}
