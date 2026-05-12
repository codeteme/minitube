function numericStringToPositiveInt(value: string): number | null {
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) return null
  return parsed
}

function stablePositiveHash(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0
  }

  // Keep IDs positive and inside signed 32-bit range expected by common SQL INTEGER.
  return Math.abs(hash) % 2_000_000_000 || 1
}

export function toApiUploaderId(userId: string | undefined | null): number | null {
  if (!userId) return null

  const direct = numericStringToPositiveInt(userId)
  if (direct !== null) return direct

  return stablePositiveHash(userId)
}
