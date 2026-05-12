const DASHBOARD_API_BASE_URL = (
  import.meta.env.VITE_DASHBOARD_API_BASE_URL || 'http://localhost:8004'
).replace(/\/$/, '')

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) return body.detail
  } catch {
    // Ignore parse failures and fallback to HTTP status.
  }
  return `Request failed with status ${response.status}`
}

export interface AiSummaryResult {
  video_id: string
  status: 'pending' | 'queued' | 'processing' | 'ready' | 'failed'
  summary: string | null
  source_kind: 'subtitle_text' | 'video_metadata' | null
  generated_at: string | null
  provider: string | null
  error_message: string | null
  cached: boolean
  retry_count: number
  duration_ms: number | null
  updated_at: string | null
}

export interface AiTagsResult {
  video_id: string
  tags: string[]
  primary_category?: string | null
  provider?: string
  generated_at?: string
}

export interface AiTagTaxonomyItem {
  canonical_tag: string
  display_name: string
  category: string
}

export interface AiTagTaxonomyResult {
  tags: AiTagTaxonomyItem[]
}

export async function summarizeVideo(payload: {
  videoId: string
  subtitleText?: string
  maxSentences?: number
  forceRefresh?: boolean
}): Promise<AiSummaryResult> {
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/ai/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_id: payload.videoId,
      subtitle_text: payload.subtitleText,
      max_sentences: payload.maxSentences ?? 3,
      force_refresh: payload.forceRefresh ?? false,
    }),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return (await response.json()) as AiSummaryResult
}

export async function fetchAiSummaryStatus(videoId: string): Promise<AiSummaryResult> {
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/ai/summarize/${videoId}`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as AiSummaryResult
}

export async function retryAiSummary(videoId: string, maxSentences = 3): Promise<AiSummaryResult> {
  const response = await fetch(
    `${DASHBOARD_API_BASE_URL}/ai/summarize/${videoId}/retry?max_sentences=${maxSentences}`,
    { method: 'POST' },
  )
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as AiSummaryResult
}

export async function generateAiTags(videoId: string, maxTags = 5): Promise<AiTagsResult> {
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/ai/tagging`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, max_tags: maxTags }),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as AiTagsResult
}

export async function fetchAiTags(videoId: string): Promise<AiTagsResult> {
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/ai/tags/${videoId}`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as AiTagsResult
}

export async function fetchAiTagTaxonomy(): Promise<AiTagTaxonomyResult> {
  const response = await fetch(`${DASHBOARD_API_BASE_URL}/ai/tag-taxonomy`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return (await response.json()) as AiTagTaxonomyResult
}
