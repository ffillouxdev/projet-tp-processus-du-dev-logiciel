import type { BracketPlayer } from './BracketMatch.vue'

export interface SwissMatchResult {
  id: string | number
  group: string
  players: readonly [BracketPlayer, BracketPlayer]
}

export type SwissRoundResults = readonly SwissMatchResult[]
